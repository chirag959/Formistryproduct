package com.hypemarketer.callvault.whatsapp

import android.app.Service
import android.content.Intent
import android.os.IBinder

/**
 * Phase 3 stub: captures WhatsApp call audio via MediaProjection + AudioPlaybackCapture.
 *
 * Must run as a foregroundServiceType="mediaProjection" service (declared in the manifest)
 * before calling MediaProjection.createVirtualDisplay / startRecording. The projection token
 * comes from [WhatsAppCallListener] (or the onboarding flow) via the screen-capture consent
 * dialog.
 *
 * Output target: same recordingsDir as phone calls, M4A AAC 64 kbps mono. After stop, insert
 * a RecordingEntity with source = CallSource.WHATSAPP and enqueue DriveSync.
 */
class WhatsAppRecordingService : Service() {
    override fun onBind(intent: Intent?): IBinder? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        // TODO: start foreground with FOREGROUND_SERVICE_TYPE_MEDIA_PROJECTION; consume the
        // MediaProjection token from the Intent extras; configure
        // AudioPlaybackCaptureConfiguration to capture com.whatsapp's MEDIA stream.
        stopSelf()
        return START_NOT_STICKY
    }
}
