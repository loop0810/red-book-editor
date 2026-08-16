import 'dart:async';
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

  Future<AgentRun> createAgentRun({
    required String accountId,
    required String columnId,
    required SourceExperience source,
    required StyleForm form,
  }) async {
    // 异步生成先创建服务端 AgentRun，再通过事件流读取进度；页面不直接等待模型 HTTP 请求。
    final response = await _client.post(
      Uri.parse('$baseUrl/api/v1/agent-runs'),
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
    return AgentRun.fromJson(jsonDecode(response.body) as Map<String, dynamic>);
  }

  Future<AgentRun> getAgentRun({required String runId}) async {
    final response = await _client.get(
      Uri.parse('$baseUrl/api/v1/agent-runs/$runId'),
    );
    if (response.statusCode >= 400) {
      throw ApiRequestException(response.statusCode, response.body);
    }
    return AgentRun.fromJson(jsonDecode(response.body) as Map<String, dynamic>);
  }

  Future<AgentRun> cancelAgentRun({required String runId}) async {
    final response = await _client.post(
      Uri.parse('$baseUrl/api/v1/agent-runs/$runId/cancel'),
    );
    if (response.statusCode >= 400) {
      throw ApiRequestException(response.statusCode, response.body);
    }
    return AgentRun.fromJson(jsonDecode(response.body) as Map<String, dynamic>);
  }

  Future<AgentRun> resumeAgentRun({required String runId}) async {
    final response = await _client.post(
      Uri.parse('$baseUrl/api/v1/agent-runs/$runId/resume'),
    );
    if (response.statusCode >= 400) {
      throw ApiRequestException(response.statusCode, response.body);
    }
    return AgentRun.fromJson(jsonDecode(response.body) as Map<String, dynamic>);
  }

  Future<NoteDraft> getNote({required String noteId}) async {
    final response = await _client.get(
      Uri.parse('$baseUrl/api/v1/notes/$noteId'),
    );
    if (response.statusCode >= 400) {
      throw ApiRequestException(response.statusCode, response.body);
    }
    return NoteDraft.fromJson(
      jsonDecode(response.body) as Map<String, dynamic>,
    );
  }

  Stream<AgentRunEvent> watchAgentRunEvents({
    required String runId,
    int after = 0,
  }) async* {
    var cursor = after;
    var reconnects = 0;
    while (true) {
      try {
        var terminal = false;
        await for (final event in _watchAgentRunEventsOnce(
          runId: runId,
          after: cursor,
        )) {
          if (event.sequence <= cursor) continue;
          cursor = event.sequence;
          yield event;
          if (_isTerminalAgentEvent(event)) terminal = true;
        }
        if (terminal) return;
        final current = await getAgentRun(runId: runId);
        if (_isTerminalStatus(current.status)) return;
      } on ApiRequestException {
        rethrow;
      } on SocketException catch (_) {
        reconnects++;
        if (reconnects > 3) rethrow;
      } on http.ClientException catch (_) {
        reconnects++;
        if (reconnects > 3) rethrow;
      } on TimeoutException catch (_) {
        reconnects++;
        if (reconnects > 3) rethrow;
      }
      await Future<void>.delayed(Duration(milliseconds: 100 * reconnects));
    }
  }

  Stream<AgentRunEvent> _watchAgentRunEventsOnce({
    required String runId,
    required int after,
  }) async* {
    final uri = Uri.parse(
      '$baseUrl/api/v1/agent-runs/$runId/events',
    ).replace(queryParameters: {'after': '$after'});
    final response = await _client.send(http.Request('GET', uri));
    if (response.statusCode >= 400) {
      final error = await http.Response.fromStream(response);
      throw ApiRequestException(error.statusCode, error.body);
    }
    var buffer = '';
    await for (final chunk in utf8.decoder.bind(response.stream)) {
      buffer += chunk;
      var separator = buffer.indexOf('\n\n');
      while (separator >= 0) {
        final event = _agentRunEventFromSse(buffer.substring(0, separator));
        if (event != null) yield event;
        buffer = buffer.substring(separator + 2);
        separator = buffer.indexOf('\n\n');
      }
    }
    if (buffer.trim().isNotEmpty) {
      final event = _agentRunEventFromSse(buffer);
      if (event != null) yield event;
    }
  }

  Future<StyledNoteResponse> generateNoteWithProgress({
    required String accountId,
    required String columnId,
    required SourceExperience source,
    required StyleForm form,
    void Function(AgentRunEvent event)? onEvent,
    void Function(AgentRun run)? onRunCreated,
  }) async {
    final run = await createAgentRun(
      accountId: accountId,
      columnId: columnId,
      source: source,
      form: form,
    );
    onRunCreated?.call(run);
    return _finishAgentRunWithProgress(run, onEvent: onEvent);
  }

  Future<StyledNoteResponse> resumeAgentRunWithProgress({
    required String runId,
    void Function(AgentRunEvent event)? onEvent,
    void Function(AgentRun run)? onRunCreated,
  }) async {
    final run = await resumeAgentRun(runId: runId);
    onRunCreated?.call(run);
    return _finishAgentRunWithProgress(run, onEvent: onEvent);
  }

  Future<StyledNoteResponse> _finishAgentRunWithProgress(
    AgentRun run, {
    void Function(AgentRunEvent event)? onEvent,
  }) async {
    final trace = <AgentTraceStep>[];
    // SSE 只接收阶段/模型/工具的摘要，用于 UI 展示；终态后重新读取 Note，
    // 这样客户端不会把事件摘要误当成最终草稿来源。
    await for (final event in watchAgentRunEvents(runId: run.runId)) {
      onEvent?.call(event);
      if (event.eventType == 'phase' ||
          event.eventType == 'model' ||
          event.eventType == 'tool') {
        trace.add(
          AgentTraceStep(
            order: event.sequence,
            kind: event.eventType == 'model' || event.eventType == 'tool'
                ? event.eventType
                : 'phase',
            label: event.label,
            summary: event.summary,
            phase: event.phase,
          ),
        );
      }
    }
    final finished = await getAgentRun(runId: run.runId);
    // completed 才允许进入编辑器；failed/cancelled/interrupted 必须保留为可恢复错误。
    if (finished.status != 'completed') {
      throw ApiRequestException(
        409,
        jsonEncode({
          'status': finished.status,
          'failure_code': finished.failureCode,
        }),
      );
    }
    return StyledNoteResponse(
      draft: await getNote(noteId: finished.noteId),
      agentTrace: trace,
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

  Future<FieldSuggestion> regenerateField({
    required NoteDraft draft,
    required String field,
    StyleForm? form,
  }) async {
    // 字段重生成返回候选历史，不直接改写当前 Note；采纳动作由编辑器另行确认并同步状态。
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
    return FieldSuggestion.fromJson(
      jsonDecode(response.body) as Map<String, dynamic>,
    );
  }

  Future<List<FieldSuggestion>> listSuggestions({
    required String noteId,
  }) async {
    final response = await _client.get(
      Uri.parse('$baseUrl/api/v1/notes/$noteId/suggestions'),
    );
    if (response.statusCode >= 400) {
      throw ApiRequestException(response.statusCode, response.body);
    }
    return (jsonDecode(response.body) as List<dynamic>)
        .map((json) => FieldSuggestion.fromJson(json as Map<String, dynamic>))
        .toList();
  }

  Future<FieldSuggestion> updateSuggestionStatus({
    required String noteId,
    required String suggestionId,
    required SuggestionStatus status,
  }) async {
    // 状态更新带有 note_id/suggestion_id 双重范围，服务端据此阻止跨笔记误操作。
    final response = await _client.patch(
      Uri.parse('$baseUrl/api/v1/notes/$noteId/suggestions/$suggestionId'),
      headers: {'content-type': 'application/json'},
      body: jsonEncode({'status': suggestionStatusToApi(status)}),
    );
    if (response.statusCode >= 400) {
      throw ApiRequestException(response.statusCode, response.body);
    }
    return FieldSuggestion.fromJson(
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
        'style_form': draft.styleForm == null
            ? null
            : styleFormToApi(draft.styleForm!),
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

AgentRunEvent? _agentRunEventFromSse(String block) {
  final data = block
      .split('\n')
      .where((line) => line.startsWith('data:'))
      .map((line) => line.substring(5).trim())
      .join();
  if (data.isEmpty) return null;
  return AgentRunEvent.fromJson(jsonDecode(data) as Map<String, dynamic>);
}

bool _isTerminalAgentEvent(AgentRunEvent event) {
  return _isTerminalStatus(event.status) ||
      event.eventType == 'run.completed' ||
      event.eventType == 'run.failed' ||
      event.eventType == 'run.cancelled' ||
      event.eventType == 'run.interrupted';
}

bool _isTerminalStatus(String? status) {
  return status == 'completed' ||
      status == 'failed' ||
      status == 'cancelled' ||
      status == 'interrupted';
}
