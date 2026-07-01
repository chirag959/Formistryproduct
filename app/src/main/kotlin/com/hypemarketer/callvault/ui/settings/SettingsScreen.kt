package com.hypemarketer.callvault.ui.settings

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SettingsScreen(onBack: () -> Unit) {
    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Settings") },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Back")
                    }
                },
            )
        },
    ) { inner ->
        Column(
            modifier = Modifier.padding(inner).fillMaxSize().padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Text("What's wired", style = MaterialTheme.typography.titleMedium)
            Text(
                "✓ Phone call auto-recording (Phase 1)\n" +
                    "✓ Local library + search\n" +
                    "✓ Gemini 2.5 Flash transcription — reads key from BuildConfig " +
                    "(app/secrets.properties → GEMINI_API_KEY)",
                style = MaterialTheme.typography.bodyMedium,
            )
            Text("Still to build", style = MaterialTheme.typography.titleMedium)
            Text(
                "• Google sign-in for Drive + resumable upload (Phase 2)\n" +
                    "• WhatsApp call capture via MediaProjection (Phase 3)\n" +
                    "• Drive folder picker (default CallVault/YYYY-MM/)\n" +
                    "• Runtime Gemini key entry via EncryptedSharedPreferences\n" +
                    "• Auto-record toggles: Phone / WhatsApp\n" +
                    "• Force-speakerphone toggle\n" +
                    "• Local retention (auto-delete after N days)\n" +
                    "• Consent disclaimer (PRD §10)",
                style = MaterialTheme.typography.bodyMedium,
            )
        }
    }
}
