package com.hypemarketer.callvault.ui.player

import android.media.MediaPlayer
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Pause
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material3.Button
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.hypemarketer.callvault.CallVaultApp
import com.hypemarketer.callvault.data.db.RecordingEntity

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun PlayerScreen(recordingId: Long, onBack: () -> Unit) {
    var recording by remember { mutableStateOf<RecordingEntity?>(null) }

    LaunchedEffect(recordingId) {
        recording = CallVaultApp.get().recordings.get(recordingId)
    }

    val player = remember { MediaPlayer() }
    var playing by remember { mutableStateOf(false) }
    var prepared by remember { mutableStateOf(false) }

    DisposableEffect(recording?.localPath) {
        val path = recording?.localPath
        if (path != null) {
            runCatching {
                player.reset()
                player.setDataSource(path)
                player.setOnPreparedListener { prepared = true }
                player.setOnCompletionListener { playing = false }
                player.prepareAsync()
            }
        }
        onDispose {
            runCatching { if (player.isPlaying) player.stop() }
            runCatching { player.release() }
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(recording?.contactName ?: "Recording") },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Back")
                    }
                },
            )
        },
    ) { inner ->
        val r = recording
        Column(
            modifier = Modifier
                .padding(inner)
                .fillMaxSize()
                .verticalScroll(rememberScrollState())
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp),
        ) {
            if (r == null) {
                Text("Loading…")
            } else {
                Text(r.contactName, style = MaterialTheme.typography.headlineSmall)
                Text("${r.source.name} • ${r.durationSec}s")
                Text(r.phoneNumber ?: "—", style = MaterialTheme.typography.bodySmall)

                Button(
                    enabled = prepared && r.localPath != null,
                    onClick = {
                        if (playing) {
                            player.pause(); playing = false
                        } else {
                            player.start(); playing = true
                        }
                    },
                ) {
                    Icon(
                        if (playing) Icons.Filled.Pause else Icons.Filled.PlayArrow,
                        contentDescription = null,
                    )
                    Text(if (playing) " Pause" else " Play")
                }

                Text("Transcript", style = MaterialTheme.typography.titleMedium)
                Text(r.transcript ?: "No transcript yet.", style = MaterialTheme.typography.bodyMedium)
            }
        }
    }
}
