package com.hypemarketer.callvault.ui.library

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.hypemarketer.callvault.data.db.CallSource
import com.hypemarketer.callvault.data.db.RecordingEntity
import com.hypemarketer.callvault.data.db.TranscriptStatus
import com.hypemarketer.callvault.data.db.UploadStatus
import java.text.DateFormat
import java.util.Date

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun LibraryScreen(
    onOpenRecording: (Long) -> Unit,
    onOpenSettings: () -> Unit,
    vm: LibraryViewModel = viewModel(),
) {
    val recordings by vm.recordings.collectAsStateWithLifecycle()
    val query by vm.query.collectAsStateWithLifecycle()

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("CallVault") },
                actions = {
                    IconButton(onClick = onOpenSettings) {
                        Icon(Icons.Filled.Settings, contentDescription = "Settings")
                    }
                },
            )
        },
    ) { inner ->
        Column(modifier = Modifier.padding(inner).fillMaxSize()) {
            OutlinedTextField(
                value = query,
                onValueChange = vm::setQuery,
                label = { Text("Search by contact, number, or transcript") },
                modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 8.dp),
                singleLine = true,
            )

            if (recordings.isEmpty()) {
                Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    Text(
                        "No recordings yet.\nMake or receive a call to test.",
                        style = MaterialTheme.typography.bodyMedium,
                    )
                }
            } else {
                LazyColumn(modifier = Modifier.fillMaxSize()) {
                    items(recordings, key = { it.id }) { rec ->
                        RecordingRow(
                            rec = rec,
                            onOpen = { onOpenRecording(rec.id) },
                            onDelete = { vm.delete(rec.id) },
                        )
                        HorizontalDivider()
                    }
                }
            }
        }
    }
}

@Composable
private fun RecordingRow(
    rec: RecordingEntity,
    onOpen: () -> Unit,
    onDelete: () -> Unit,
) {
    Row(
        modifier = Modifier.fillMaxWidth().clickable(onClick = onOpen).padding(16.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Column(modifier = Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(4.dp)) {
            Text(rec.contactName, style = MaterialTheme.typography.titleMedium)
            Text(
                "${labelFor(rec.source)} • ${formatTimestamp(rec.startedAt)} • ${formatDuration(rec.durationSec)}",
                style = MaterialTheme.typography.bodySmall,
            )
            Text(
                "Upload: ${rec.uploadStatus.name.lowercase()} • Transcript: ${rec.transcriptStatus.name.lowercase()}",
                style = MaterialTheme.typography.labelSmall,
                color = colorForStatus(rec.uploadStatus, rec.transcriptStatus),
            )
        }
        Spacer(Modifier.height(0.dp))
        IconButton(onClick = onDelete) {
            Icon(Icons.Filled.Delete, contentDescription = "Delete")
        }
    }
}

@Composable
private fun colorForStatus(upload: UploadStatus, transcript: TranscriptStatus) =
    when {
        upload == UploadStatus.FAILED || transcript == TranscriptStatus.FAILED ->
            MaterialTheme.colorScheme.error
        upload == UploadStatus.UPLOADED && transcript == TranscriptStatus.DONE ->
            MaterialTheme.colorScheme.secondary
        else -> MaterialTheme.colorScheme.onSurfaceVariant
    }

private fun labelFor(source: CallSource): String = when (source) {
    CallSource.PHONE_INCOMING -> "Incoming"
    CallSource.PHONE_OUTGOING -> "Outgoing"
    CallSource.WHATSAPP -> "WhatsApp"
}

private fun formatTimestamp(ts: Long): String =
    DateFormat.getDateTimeInstance(DateFormat.MEDIUM, DateFormat.SHORT).format(Date(ts))

private fun formatDuration(sec: Int): String {
    val m = sec / 60
    val s = sec % 60
    return "%d:%02d".format(m, s)
}
