package com.hypemarketer.callvault.recording

import android.app.Notification
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.media.AudioManager
import android.os.Build
import android.os.IBinder
import android.util.Log
import androidx.core.app.NotificationCompat
import com.hypemarketer.callvault.CallVaultApp
import com.hypemarketer.callvault.MainActivity
import com.hypemarketer.callvault.R
import com.hypemarketer.callvault.data.db.CallSource
import com.hypemarketer.callvault.data.db.RecordingEntity
import com.hypemarketer.callvault.data.db.TranscriptStatus
import com.hypemarketer.callvault.data.db.UploadStatus
import com.hypemarketer.callvault.sync.DriveSync
import com.hypemarketer.callvault.util.AudioFileNamer
import com.hypemarketer.callvault.util.ContactResolver
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.launch
import java.io.File

/**
 * Foreground service that owns the AudioRecorder for the duration of a call.
 *
 * Receives lifecycle commands from [PhoneCallReceiver]:
 *  - ACTION_START with phone number + direction
 *  - ACTION_STOP
 *
 * On stop, inserts a [RecordingEntity] and enqueues Drive upload (Phase 2).
 */
class CallRecordingService : Service() {

    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private val recorder by lazy { AudioRecorder(this) }
    private var startedAt: Long = 0L
    private var currentNumber: String? = null
    private var currentSource: CallSource = CallSource.PHONE_INCOMING
    private var currentFile: File? = null

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            ACTION_START -> {
                currentNumber = intent.getStringExtra(EXTRA_NUMBER)
                currentSource = intent.getStringExtra(EXTRA_DIRECTION)
                    ?.let { runCatching { CallSource.valueOf(it) }.getOrNull() }
                    ?: CallSource.PHONE_INCOMING
                startForegroundCompat()
                startRecording()
            }
            ACTION_STOP -> {
                stopRecording()
                stopForegroundAndSelf()
            }
            else -> stopForegroundAndSelf()
        }
        return START_NOT_STICKY
    }

    private fun startRecording() {
        if (recorder.isRecording()) return
        startedAt = System.currentTimeMillis()
        val dir = recordingsDir(this)
        val baseName = AudioFileNamer.fileBaseName(
            contactName = currentNumber?.let { ContactResolver.lookup(this, it) } ?: "Unknown",
            startedAt = startedAt,
        )
        try {
            currentFile = recorder.start(dir, baseName)
        } catch (t: Throwable) {
            Log.e(TAG, "Failed to start MediaRecorder; retrying with MIC + speakerphone", t)
            forceSpeakerphone(true)
            currentFile = runCatching {
                recorder.start(dir, baseName, audioSource = android.media.MediaRecorder.AudioSource.MIC)
            }.getOrNull()
        }
    }

    private fun stopRecording() {
        val file = recorder.stop() ?: currentFile
        val endedAt = System.currentTimeMillis()
        val duration = ((endedAt - startedAt) / 1000).toInt().coerceAtLeast(0)
        forceSpeakerphone(false)

        if (file == null || !file.exists() || file.length() < 1024L) {
            Log.w(TAG, "No audio captured; skipping DB insert. file=$file size=${file?.length()}")
            return
        }
        val number = currentNumber
        val contact = number?.let { ContactResolver.lookup(this, it) } ?: "Unknown"

        scope.launch {
            val app = applicationContext as CallVaultApp
            val id = app.recordings.insert(
                RecordingEntity(
                    contactName = contact,
                    phoneNumber = number,
                    source = currentSource,
                    startedAt = startedAt,
                    durationSec = duration,
                    localPath = file.absolutePath,
                    driveFileId = null,
                    transcript = null,
                    uploadStatus = UploadStatus.PENDING,
                    transcriptStatus = TranscriptStatus.PENDING,
                ),
            )
            DriveSync.enqueueUpload(this@CallRecordingService, id)
        }
    }

    private fun startForegroundCompat() {
        val openApp = PendingIntent.getActivity(
            this,
            0,
            Intent(this, MainActivity::class.java),
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT,
        )
        val notification: Notification = NotificationCompat.Builder(this, CallVaultApp.CHANNEL_RECORDING)
            .setContentTitle(getString(R.string.notification_recording_title))
            .setContentText(getString(R.string.notification_recording_text))
            .setSmallIcon(android.R.drawable.ic_btn_speak_now)
            .setOngoing(true)
            .setContentIntent(openApp)
            .build()

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            startForeground(
                NOTIFICATION_ID,
                notification,
                ServiceInfo.FOREGROUND_SERVICE_TYPE_MICROPHONE,
            )
        } else {
            startForeground(NOTIFICATION_ID, notification)
        }
    }

    private fun stopForegroundAndSelf() {
        stopForeground(STOP_FOREGROUND_REMOVE)
        stopSelf()
    }

    private fun forceSpeakerphone(on: Boolean) {
        runCatching {
            val am = getSystemService(Context.AUDIO_SERVICE) as AudioManager
            @Suppress("DEPRECATION")
            am.isSpeakerphoneOn = on
        }
    }

    override fun onDestroy() {
        if (recorder.isRecording()) stopRecording()
        scope.cancel()
        super.onDestroy()
    }

    companion object {
        private const val TAG = "CallRecordingService"
        private const val NOTIFICATION_ID = 7301

        const val ACTION_START = "com.hypemarketer.callvault.action.START"
        const val ACTION_STOP = "com.hypemarketer.callvault.action.STOP"
        const val EXTRA_NUMBER = "number"
        const val EXTRA_DIRECTION = "direction"

        fun recordingsDir(context: Context): File =
            File(context.getExternalFilesDir(null) ?: context.filesDir, "recordings")
    }
}
