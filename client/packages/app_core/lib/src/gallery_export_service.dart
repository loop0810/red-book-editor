import 'package:flutter/services.dart';

/// 通过平台通道把图片字节保存到系统相册，供手动发布小红书时使用。
class GalleryExportService {
  const GalleryExportService();

  static const MethodChannel _channel = MethodChannel(
    'red_book_editor/gallery',
  );

  Future<void> saveImage({
    required Uint8List bytes,
    required String filename,
  }) async {
    try {
      await _channel.invokeMethod<void>('saveImage', {
        'bytes': bytes,
        'filename': filename,
      });
    } on PlatformException catch (error) {
      throw ExportException(error.message ?? '保存图片失败');
    } on MissingPluginException {
      throw const ExportException('当前平台不支持保存到相册');
    }
  }
}

class ExportException implements Exception {
  const ExportException(this.message);

  final String message;

  @override
  String toString() => message;
}
