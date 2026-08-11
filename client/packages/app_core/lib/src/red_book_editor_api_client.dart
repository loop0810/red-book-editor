import 'dart:convert';
import 'dart:io';

import 'package:http/http.dart' as http;

import 'content_workflow_models.dart';

class RedBookEditorApiClient {
  RedBookEditorApiClient({
    http.Client? client,
    this.baseUrl = 'http://127.0.0.1:8000',
  }) : _client = client ?? http.Client();

  final http.Client _client;
  final String baseUrl;

  // 这个类是 Flutter 与 FastAPI 之间的边界：
  // 上层页面使用 Dart model，不直接拼 URL 或解析 JSON。
  Future<http.Response> getLiveHealth() =>
      _client.get(Uri.parse('$baseUrl/health/live'));

  Future<StyledNoteResponse> generateNote({
    required String accountId,
    required String columnId,
    required SourceExperience source,
    required StyleForm form,
  }) async {
    // SourceExperience 是用户提供的事实来源，form 是期望的表达形式。
    // 服务端会根据这两个输入生成草稿，而不是客户端自己调用模型。
    final response = await _client.post(
      Uri.parse('$baseUrl/api/v1/notes/generate'),
      headers: {'content-type': 'application/json'},
      body: jsonEncode({
        'account_id': accountId,
        'column_id': columnId,
        'form': styleFormToApi(form),
        'source': source.toJson(),
      }),
    );
    if (response.statusCode >= 400) {
      throw ApiRequestException(response.statusCode, response.body);
    }
    return StyledNoteResponse.fromJson(
      // JSON 在 API 边界只解析一次，之后页面使用类型安全的 Dart 对象。
      jsonDecode(response.body) as Map<String, dynamic>,
    );
  }

  Future<StyledNoteResponse> restyleNote({
    required NoteDraft draft,
    required StyleForm form,
  }) async {
    // 局部重生成仍携带完整 draft，但服务端只应该更新 field 指定的字段。
    // 这样用户已经手动修改的其他字段不会被模型覆盖。
    final response = await _client.post(
      Uri.parse('$baseUrl/api/v1/notes/style'),
      headers: {'content-type': 'application/json'},
      body: jsonEncode({'draft': draft.toJson(), 'form': styleFormToApi(form)}),
    );
    if (response.statusCode >= 400) {
      throw ApiRequestException(response.statusCode, response.body);
    }
    return StyledNoteResponse.fromJson(
      jsonDecode(response.body) as Map<String, dynamic>,
    );
  }

  Future<NoteDraft> regenerateField({
    required NoteDraft draft,
    required String field,
    StyleForm? form,
  }) async {
    final response = await _client.post(
      Uri.parse('$baseUrl/api/v1/notes/regenerate-field'),
      headers: {'content-type': 'application/json'},
      body: jsonEncode({
        'draft': draft.toJson(),
        'field': field,
        if (form != null) 'form': styleFormToApi(form),
      }),
    );
    if (response.statusCode >= 400) {
      throw ApiRequestException(response.statusCode, response.body);
    }
    return NoteDraft.fromJson(
      jsonDecode(response.body) as Map<String, dynamic>,
    );
  }

  Future<NoteDraft> saveNote({required NoteDraft draft}) async {
    final response = await _client.put(
      Uri.parse('$baseUrl/api/v1/notes/${draft.noteId}'),
      headers: {'content-type': 'application/json'},
      body: jsonEncode({
        'topic_angle': draft.topicAngle,
        'title_candidates': draft.titleCandidates,
        'body': draft.body,
        'hashtags': draft.hashtags,
        'cover_copy': draft.coverCopy,
        'image_suggestions': draft.imageSuggestions,
      }),
    );
    if (response.statusCode >= 400) {
      throw ApiRequestException(response.statusCode, response.body);
    }
    return NoteDraft.fromJson(
      jsonDecode(response.body) as Map<String, dynamic>,
    );
  }

  Future<List<NoteDraft>> listNotes({required String accountId}) async {
    final response = await _client.get(
      Uri.parse('$baseUrl/api/v1/accounts/$accountId/notes'),
    );
    if (response.statusCode >= 400) {
      throw ApiRequestException(response.statusCode, response.body);
    }
    return (jsonDecode(response.body) as List<dynamic>)
        .map((json) => NoteDraft.fromJson(json as Map<String, dynamic>))
        .toList();
  }

  Future<List<NoteDraftVersion>> listNoteVersions({
    required String noteId,
  }) async {
    final response = await _client.get(
      Uri.parse('$baseUrl/api/v1/notes/$noteId/versions'),
    );
    if (response.statusCode >= 400) {
      throw ApiRequestException(response.statusCode, response.body);
    }
    return (jsonDecode(response.body) as List<dynamic>)
        .map((json) => NoteDraftVersion.fromJson(json as Map<String, dynamic>))
        .toList();
  }

  Future<List<Asset>> listAssets({required String accountId}) async {
    final response = await _client.get(
      Uri.parse('$baseUrl/api/v1/accounts/$accountId/assets'),
    );
    if (response.statusCode >= 400) {
      throw ApiRequestException(response.statusCode, response.body);
    }
    return (jsonDecode(response.body) as List<dynamic>)
        .map((json) => Asset.fromJson(json as Map<String, dynamic>))
        .toList();
  }

  Future<String> uploadAsset({
    required String accountId,
    required String filePath,
    void Function(int sentBytes, int totalBytes)? onProgress,
  }) async {
    final file = File(filePath);
    final length = await file.length();
    final filename = file.uri.pathSegments.last;
    final boundary =
        '----redBookEditor${DateTime.now().microsecondsSinceEpoch}';
    final contentType = _contentTypeForFilename(filename);
    final header = utf8.encode(
      '--$boundary\r\n'
      'content-disposition: form-data; name="file"; filename="$filename"\r\n'
      'content-type: $contentType\r\n\r\n',
    );
    final tail = utf8.encode('\r\n--$boundary--\r\n');
    final total = header.length + length + tail.length;
    final request = http.StreamedRequest(
      'POST',
      Uri.parse('$baseUrl/api/v1/accounts/$accountId/assets'),
    );
    request.headers['content-type'] = 'multipart/form-data; boundary=$boundary';
    request.headers['content-length'] = '$total';
    var sent = header.length;
    request.sink.add(header);
    await for (final chunk in file.openRead()) {
      request.sink.add(chunk);
      sent += chunk.length;
      onProgress?.call(sent, total);
    }
    request.sink.add(tail);
    request.sink.close();
    final response = await http.Response.fromStream(
      await _client.send(request),
    );
    if (response.statusCode >= 400) {
      throw ApiRequestException(response.statusCode, response.body);
    }
    final json = jsonDecode(response.body) as Map<String, dynamic>;
    return json['asset_id'] as String;
  }

  Future<void> deleteAsset({required String assetId}) async {
    final response = await _client.delete(
      Uri.parse('$baseUrl/api/v1/assets/$assetId'),
    );
    if (response.statusCode >= 400) {
      throw ApiRequestException(response.statusCode, response.body);
    }
  }

  Future<List<Asset>> reorderAssets({
    required String accountId,
    required List<String> assetIds,
  }) async {
    final response = await _client.put(
      Uri.parse('$baseUrl/api/v1/accounts/$accountId/assets/order'),
      headers: {'content-type': 'application/json'},
      body: jsonEncode({'asset_ids': assetIds}),
    );
    if (response.statusCode >= 400) {
      throw ApiRequestException(response.statusCode, response.body);
    }
    return (jsonDecode(response.body) as List<dynamic>)
        .map((json) => Asset.fromJson(json as Map<String, dynamic>))
        .toList();
  }

  Future<DownloadedAsset> downloadAsset({required String assetId}) async {
    final response = await _client.get(
      Uri.parse('$baseUrl/api/v1/assets/$assetId'),
    );
    if (response.statusCode >= 400) {
      throw ApiRequestException(response.statusCode, response.body);
    }
    final filename =
        _filenameFromDisposition(response.headers['content-disposition']) ??
        'asset_$assetId.jpg';
    return DownloadedAsset(
      bytes: response.bodyBytes,
      filename: filename,
      contentType: response.headers['content-type'] ?? 'image/jpeg',
    );
  }

  Future<void> recordPublication({
    required String noteId,
    required String status,
    String? link,
    int? views,
    int? likes,
    int? saves,
    int? comments,
  }) async {
    final response = await _client.post(
      Uri.parse('$baseUrl/api/v1/notes/$noteId/publish-record'),
      headers: {'content-type': 'application/json'},
      body: jsonEncode({
        'status': status,
        'link': link,
        'views': views,
        'likes': likes,
        'saves': saves,
        'comments': comments,
      }),
    );
    if (response.statusCode >= 400) {
      throw ApiRequestException(response.statusCode, response.body);
    }
  }
}

String _contentTypeForFilename(String filename) {
  final lower = filename.toLowerCase();
  if (lower.endsWith('.png')) return 'image/png';
  if (lower.endsWith('.webp')) return 'image/webp';
  if (lower.endsWith('.heic')) return 'image/heic';
  if (lower.endsWith('.gif')) return 'image/gif';
  return 'image/jpeg';
}

String? _filenameFromDisposition(String? disposition) {
  if (disposition == null) return null;
  final match = RegExp(r'filename="?([^";]+)"?').firstMatch(disposition);
  return match?.group(1);
}

class ApiRequestException implements Exception {
  const ApiRequestException(this.statusCode, this.body);

  final int statusCode;
  final String body;
}
