package com.hypemarketer.callvault

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Scaffold
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import com.hypemarketer.callvault.ui.library.LibraryScreen
import com.hypemarketer.callvault.ui.onboarding.PermissionsScreen
import com.hypemarketer.callvault.ui.player.PlayerScreen
import com.hypemarketer.callvault.ui.settings.SettingsScreen
import com.hypemarketer.callvault.ui.theme.CallVaultTheme
import com.hypemarketer.callvault.util.PermissionHelper

class MainActivity : ComponentActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            CallVaultTheme {
                Root()
            }
        }
    }
}

private object Routes {
    const val LIBRARY = "library"
    const val PERMISSIONS = "permissions"
    const val SETTINGS = "settings"
    const val PLAYER = "player/{recordingId}"
    fun player(id: Long) = "player/$id"
}

@Composable
private fun Root() {
    val nav = rememberNavController()
    val start = if (PermissionHelper.hasCoreRecordingPermissions(CallVaultApp.get())) {
        Routes.LIBRARY
    } else {
        Routes.PERMISSIONS
    }
    Scaffold(modifier = Modifier.fillMaxSize()) { inner ->
        NavHost(
            navController = nav,
            startDestination = start,
            modifier = Modifier.padding(inner),
        ) {
            composable(Routes.PERMISSIONS) {
                PermissionsScreen(onDone = {
                    nav.navigate(Routes.LIBRARY) {
                        popUpTo(Routes.PERMISSIONS) { inclusive = true }
                    }
                })
            }
            composable(Routes.LIBRARY) {
                LibraryScreen(
                    onOpenRecording = { id -> nav.navigate(Routes.player(id)) },
                    onOpenSettings = { nav.navigate(Routes.SETTINGS) },
                )
            }
            composable(Routes.SETTINGS) {
                SettingsScreen(onBack = { nav.popBackStack() })
            }
            composable(Routes.PLAYER) { backStackEntry ->
                val id = backStackEntry.arguments?.getString("recordingId")?.toLongOrNull() ?: 0L
                PlayerScreen(recordingId = id, onBack = { nav.popBackStack() })
            }
        }
    }
}
