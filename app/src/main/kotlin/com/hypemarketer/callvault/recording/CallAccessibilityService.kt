package com.hypemarketer.callvault.recording

import android.accessibilityservice.AccessibilityService
import android.view.accessibility.AccessibilityEvent

/**
 * Stub for the accessibility-based audio routing helper described in PRD §4.1.
 *
 * Some OEM dialers (Samsung One UI, Xiaomi MIUI) suppress the audio source for non-system
 * apps even with VOICE_RECOGNITION; running an AccessibilityService gives the app a
 * privileged channel to detect call UI state and to programmatically toggle speakerphone.
 *
 * Phase 1 leaves this as a no-op. Implement once we see failure modes on the OEMs in
 * PRD §10 (Xiaomi, Samsung).
 */
class CallAccessibilityService : AccessibilityService() {
    override fun onAccessibilityEvent(event: AccessibilityEvent?) = Unit
    override fun onInterrupt() = Unit
}
