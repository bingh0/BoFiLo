package eu.schnuff.bofilo.settings

import android.content.ContentResolver
import android.content.Context
import android.net.Uri
import androidx.core.content.edit
import androidx.core.net.toUri
import androidx.preference.PreferenceManager
import eu.schnuff.bofilo.Constants
import eu.schnuff.bofilo.R

class Settings (context: Context) {
    private val p = PreferenceManager.getDefaultSharedPreferences(context)
    private val defaultWebViewUserAgent = context.getString(R.string.webview_user_agent_default)

    val showConsole
    get() = p.getBoolean(Constants.PREF_SHOW_CONSOLE, true)

    val isAdult
    get() = p.getBoolean(Constants.PREF_IS_ADULT, false)

    val includeImages: String
    get() = p.getString(Constants.PREF_INCLUDE_IMAGES, "false") ?: "false"

    val saveCache
    get() = p.getBoolean(Constants.PREF_SAVE_CACHE, false)

    val dstDir
    get() = directory(Constants.PREF_DEFAULT_DIRECTORY)

    val srcDir
    get() = directory(Constants.PREF_DEFAULT_SRC_DIRECTORY)

    /**
     * Folders are stored as the content:// tree URI the user picked. Versions up to 10 turned
     * folders on internal storage into raw file:// paths and relied on MANAGE_EXTERNAL_STORAGE
     * to write there. That permission is gone, so such a path is unusable: forget it and let the
     * user pick the folder again.
     */
    private fun directory(key: String): Uri? {
        val uri = p.getString(key, null)?.toUri() ?: return null
        if (uri.scheme == ContentResolver.SCHEME_FILE) {
            p.edit { remove(key) }
            return null
        }
        return uri
    }

    val webViewUserAgent
    get() = p.getString(Constants.PREF_WEBVIEW_USER_AGENT, defaultWebViewUserAgent)
}