package com.redbookeditor.red_book_editor

import android.content.ContentValues
import android.os.Build
import android.os.Environment
import android.provider.MediaStore
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel

class MainActivity : FlutterActivity() {
    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        MethodChannel(
            flutterEngine.dartExecutor.binaryMessenger,
            "red_book_editor/gallery",
        ).setMethodCallHandler { call, result ->
            if (call.method != "saveImage") {
                result.notImplemented()
                return@setMethodCallHandler
            }
            val bytes = call.argument<ByteArray>("bytes")
            val filename = call.argument<String>("filename") ?: "asset.jpg"
            if (bytes == null) {
                result.error("invalid_arguments", "Missing bytes", null)
                return@setMethodCallHandler
            }
            try {
                result.success(saveToGallery(bytes, filename))
            } catch (error: Exception) {
                result.error("save_failed", error.message, null)
            }
        }
    }

    private fun saveToGallery(bytes: ByteArray, filename: String): String {
        val mimeType = when (filename.substringAfterLast('.', "").lowercase()) {
            "png" -> "image/png"
            "webp" -> "image/webp"
            "heic" -> "image/heic"
            else -> "image/jpeg"
        }
        val values = ContentValues().apply {
            put(MediaStore.Images.Media.DISPLAY_NAME, filename)
            put(MediaStore.Images.Media.MIME_TYPE, mimeType)
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                put(
                    MediaStore.Images.Media.RELATIVE_PATH,
                    "${Environment.DIRECTORY_PICTURES}/RedBookEditor",
                )
                put(MediaStore.Images.Media.IS_PENDING, 1)
            }
        }
        val resolver = contentResolver
        val uri = resolver.insert(
            MediaStore.Images.Media.EXTERNAL_CONTENT_URI,
            values,
        ) ?: throw IllegalStateException("无法创建相册条目")
        resolver.openOutputStream(uri)?.use { stream ->
            stream.write(bytes)
        } ?: throw IllegalStateException("无法写入图片")
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            values.clear()
            values.put(MediaStore.Images.Media.IS_PENDING, 0)
            resolver.update(uri, values, null, null)
        }
        return uri.toString()
    }
}
