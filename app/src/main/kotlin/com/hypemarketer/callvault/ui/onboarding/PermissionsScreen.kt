package com.hypemarketer.callvault.ui.onboarding

import android.content.Intent
import android.net.Uri
import android.provider.Settings
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import com.hypemarketer.callvault.util.PermissionHelper

@Composable
fun PermissionsScreen(onDone: () -> Unit) {
    val context = LocalContext.current
    var coreGranted by remember { mutableStateOf(PermissionHelper.hasCoreRecordingPermissions(context)) }
    var listenerGranted by remember { mutableStateOf(PermissionHelper.hasNotificationListener(context)) }

    val corePermLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions(),
    ) { result ->
        coreGranted = result.values.all { it } && PermissionHelper.hasCoreRecordingPermissions(context)
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(24.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        Text("Welcome to CallVault", style = androidx.compose.material3.MaterialTheme.typography.headlineSmall)
        Text(
            "CallVault needs the permissions below to auto-record your calls, name them by " +
                "contact, and sync them to your Drive. Tap each row to grant.",
            style = androidx.compose.material3.MaterialTheme.typography.bodyMedium,
        )

        Spacer(Modifier.height(8.dp))

        PermissionRow(
            title = "Microphone, phone, contacts, notifications",
            subtitle = "Required for the recorder to capture and name calls.",
            granted = coreGranted,
            onRequest = { corePermLauncher.launch(PermissionHelper.corePermissions()) },
        )

        PermissionRow(
            title = "Battery optimization opt-out",
            subtitle = "Prevents Android from killing the recorder mid-call.",
            granted = false,
            onRequest = {
                runCatching {
                    val i = Intent(Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS).apply {
                        data = Uri.parse("package:${context.packageName}")
                    }
                    context.startActivity(i)
                }
            },
        )

        PermissionRow(
            title = "Notification access (for WhatsApp calls)",
            subtitle = "Lets CallVault detect when a WhatsApp call starts.",
            granted = listenerGranted,
            onRequest = {
                context.startActivity(Intent(Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS))
            },
        )

        PermissionRow(
            title = "Accessibility (optional, OEM workaround)",
            subtitle = "Only needed if VOICE_RECOGNITION returns silence on this phone.",
            granted = PermissionHelper.hasAccessibilityService(context),
            onRequest = {
                context.startActivity(Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS))
            },
        )

        Spacer(Modifier.height(8.dp))

        Button(
            onClick = onDone,
            enabled = coreGranted,
            modifier = Modifier.fillMaxWidth(),
        ) {
            Text(if (coreGranted) "Continue" else "Grant core permissions to continue")
        }
    }
}

@Composable
private fun PermissionRow(
    title: String,
    subtitle: String,
    granted: Boolean,
    onRequest: () -> Unit,
) {
    Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
        Text(title, style = androidx.compose.material3.MaterialTheme.typography.titleMedium)
        Text(subtitle, style = androidx.compose.material3.MaterialTheme.typography.bodySmall)
        OutlinedButton(onClick = onRequest) {
            Text(if (granted) "Granted ✓ — re-open settings" else "Grant")
        }
    }
}
