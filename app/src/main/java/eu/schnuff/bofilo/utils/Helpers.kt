package eu.schnuff.bofilo.utils

import android.content.ContentResolver
import android.net.Uri
import android.provider.DocumentsContract
import java.io.FileNotFoundException
import java.io.FileOutputStream

private const val CONTENT_SCHEME = ContentResolver.SCHEME_CONTENT

object Helpers {

    // This one helps to copy file content between uris by using ContentResolver.
    // We can copy from and to DocumentFiles and normal "file://..." (for cacheDir) uris with this function.
    fun ContentResolver.copyFile(src: Uri, dst: Uri) {
        if (src.scheme == CONTENT_SCHEME && dst.scheme == CONTENT_SCHEME) {
            DocumentsContract.copyDocument(this, src, dst) // cant copy to cache/data directory -.-
        } else {
            val input = this.openInputStream(src)?.buffered()
                ?: throw FileNotFoundException(src.toString())
            val outputStream = this.openOutputStream(dst) ?: throw FileNotFoundException(dst.toString())
            (outputStream as? FileOutputStream)?.channel?.truncate(0)
            val output = outputStream.buffered()

            while (input.available() == 0) {
                Thread.sleep(25)
            }
            while (input.available() > 0) {
                input.copyTo(output)
            }

            input.close()
            output.close()
        }
    }
}
