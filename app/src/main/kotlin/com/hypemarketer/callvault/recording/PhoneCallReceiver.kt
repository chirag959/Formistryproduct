package com.hypemarketer.callvault.recording

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.os.Build
import android.telephony.TelephonyManager
import android.util.Log
import com.hypemarketer.callvault.data.db.CallSource

/**
 * Detects call lifecycle and forwards START/STOP to [CallRecordingService].
 *
 * Phase 1 scope. PHONE_STATE broadcast carries OFFHOOK + IDLE; NEW_OUTGOING_CALL captures
 * the dialed number (since android.intent.extra.INCOMING_NUMBER was removed in Android 10+
 * unless READ_CALL_LOG is granted — which we already request).
 *
 * On Android 12+, callers should also subscribe a [android.telephony.TelephonyCallback] for
 * stricter accuracy. That can be added in PhoneCallTracker if PHONE_STATE proves unreliable.
 */
class PhoneCallReceiver : BroadcastReceiver() {

    override fun onReceive(context: Context, intent: Intent) {
        when (intent.action) {
            Intent.ACTION_NEW_OUTGOING_CALL -> {
                @Suppress("DEPRECATION")
                val number = intent.getStringExtra(Intent.EXTRA_PHONE_NUMBER)
                outgoingNumber = number
                lastDirection = CallSource.PHONE_OUTGOING
                Log.d(TAG, "outgoing → $number")
            }

            TelephonyManager.ACTION_PHONE_STATE_CHANGED -> {
                val state = intent.getStringExtra(TelephonyManager.EXTRA_STATE)
                @Suppress("DEPRECATION")
                val incoming = intent.getStringExtra(TelephonyManager.EXTRA_INCOMING_NUMBER)
                Log.d(TAG, "phone state → $state incoming=$incoming")

                when (state) {
                    TelephonyManager.EXTRA_STATE_RINGING -> {
                        lastDirection = CallSource.PHONE_INCOMING
                        if (incoming != null) outgoingNumber = incoming
                    }

                    TelephonyManager.EXTRA_STATE_OFFHOOK -> {
                        if (!isRecording) {
                            isRecording = true
                            start(context, outgoingNumber, lastDirection)
                        }
                    }

                    TelephonyManager.EXTRA_STATE_IDLE -> {
                        if (isRecording) {
                            isRecording = false
                            stop(context)
                        }
                        outgoingNumber = null
                        lastDirection = CallSource.PHONE_INCOMING
                    }
                }
            }

            Intent.ACTION_BOOT_COMPLETED -> {
                Log.d(TAG, "boot completed; receiver re-registered via manifest")
            }
        }
    }

    private fun start(context: Context, number: String?, direction: CallSource) {
        val svc = Intent(context, CallRecordingService::class.java).apply {
            action = CallRecordingService.ACTION_START
            putExtra(CallRecordingService.EXTRA_NUMBER, number)
            putExtra(CallRecordingService.EXTRA_DIRECTION, direction.name)
        }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            context.startForegroundService(svc)
        } else {
            context.startService(svc)
        }
    }

    private fun stop(context: Context) {
        val svc = Intent(context, CallRecordingService::class.java).apply {
            action = CallRecordingService.ACTION_STOP
        }
        context.startService(svc)
    }

    companion object {
        private const val TAG = "PhoneCallReceiver"

        // Receiver instances are recreated per broadcast, so per-call state lives in the companion.
        @Volatile private var outgoingNumber: String? = null
        @Volatile private var lastDirection: CallSource = CallSource.PHONE_INCOMING
        @Volatile private var isRecording: Boolean = false
    }
}
