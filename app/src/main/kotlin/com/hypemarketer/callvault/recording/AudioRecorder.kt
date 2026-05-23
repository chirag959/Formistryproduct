package com.hypemarketer.callvault.recording

import android.content.Context
import android.media.MediaRecorder
import android.os.Build
import android.util.Log
import java.io.File

/**
 * Thin MediaRecorder wrapper for Phase 1.
 *
 * Uses VOICE_RECOGNITION as primary (per PRD §4.1 — VOICE_CALL is blocked for non-system apps
 * on Android 10+). Falls back to MIC + speakerphone if VOICE_RECOGNITION returns silence.
 *
 * Output: M4A / AAC, 64 kbps mono — ~30 MB per hour. Good enough for transcription.
 */
class AudioRecorder(private val context: Context) {

    private var recorder: MediaRecorder? = null
    var outputFile: File? = null
        private set

    fun start(outputDir: File, baseName: String, audioSource: Int = MediaRecorder.AudioSource.VOICE_RECOGNITION): File {
        check(recorder == null) { "Recorder already running" }
        outputDir.mkdirs()
        val file = File(outputDir, "$baseName.m4a")
        outputFile = file

        @Suppress("DEPRECATION")
        val r = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            MediaRecorder(context)
        } else {
            MediaRecorder()
        }
        r.apply {
            setAudioSource(audioSource)
            setOutputFormat(MediaRecorder.OutputFormat.MPEG_4)
            setAudioEncoder(MediaRecorder.AudioEncoder.AAC)
            setAudioSamplingRate(SAMPLE_RATE_HZ)
            setAudioEncodingBitRate(BITRATE_BPS)
            setAudioChannels(1)
            setOutputFile(file.absolutePath)
            prepare()
            start()
        }
        recorder = r
        Log.i(TAG, "Recording started → ${file.absolutePath}")
        return file
    }

    fun stop(): File? {
        val r = recorder ?: return null
        try {
            r.stop()
        } catch (t: Throwable) {
            Log.w(TAG, "stop() threw; file may be short or empty", t)
        }
        runCatching { r.release() }
        recorder = null
        Log.i(TAG, "Recording stopped → ${outputFile?.absolutePath}")
        return outputFile
    }

    fun isRecording(): Boolean = recorder != null

    companion object {
        private const val TAG = "AudioRecorder"
        private const val SAMPLE_RATE_HZ = 16_000
        private const val BITRATE_BPS = 64_000
    }
}
