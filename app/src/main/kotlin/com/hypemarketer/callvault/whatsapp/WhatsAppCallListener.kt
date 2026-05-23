package com.hypemarketer.callvault.whatsapp

import android.service.notification.NotificationListenerService
import android.service.notification.StatusBarNotification
import android.util.Log

/**
 * Phase 3 stub.
 *
 * TODO(Atharva):
 *   1. In onNotificationPosted: check sbn.packageName == "com.whatsapp" or "com.whatsapp.w4b".
 *   2. Inspect Notification.category — WhatsApp posts CATEGORY_CALL or CATEGORY_PROGRESS during
 *      an ongoing call. The notification text/title contains the contact name.
 *   3. When a call starts: request MediaProjection consent (this requires an Activity round-trip —
 *      either prompt the user upfront once and cache the projection token, or pop a transparent
 *      Activity on call start).
 *   4. Hand the MediaProjection to [WhatsAppRecordingService] which starts an
 *      AudioPlaybackCaptureConfiguration on AudioRecord (Android 10+).
 *   5. In onNotificationRemoved: stop the WhatsAppRecordingService.
 */
class WhatsAppCallListener : NotificationListenerService() {

    override fun onNotificationPosted(sbn: StatusBarNotification) {
        if (sbn.packageName !in WHATSAPP_PACKAGES) return
        Log.d(TAG, "WhatsApp notification: ${sbn.notification.category} from ${sbn.packageName}")
        // TODO: detect call-start signature and trigger WhatsAppRecordingService.
    }

    override fun onNotificationRemoved(sbn: StatusBarNotification) {
        if (sbn.packageName !in WHATSAPP_PACKAGES) return
        // TODO: stop recording if active.
    }

    companion object {
        private const val TAG = "WhatsAppCallListener"
        private val WHATSAPP_PACKAGES = setOf("com.whatsapp", "com.whatsapp.w4b")
    }
}
