import 'dart:convert';
import 'dart:io';

import 'package:app_core/app_core.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

const _accountId = '00000000-0000-0000-0000-000000000001';
const _columnId = '00000000-0000-0000-0000-000000000002';

const _draftJson = {
  'note_id': '11111111-1111-1111-1111-111111111111',
  'account_id': _accountId,
  'column_id': _columnId,
  'status': 'ready',
  'topic_angle': '19个月宝宝的睡前哭闹记录',
  'title_candidates': ['标题一', '标题二'],
  'body': '宝宝19个月时，遇到了睡前哭闹。',
  'hashtags': ['#育儿日常'],
  'cover_copy': '睡前哭闹',
  'image_suggestions': ['场景照片'],
  'style_form': 'experience',
  'source': {
    'baby_month': 19,
    'scenario': '睡前哭闹',
    'actions': ['固定绘本时间'],
    'observations': '入睡过程变顺了一些',
    'notes': '补充说明',
    'asset_ids': ['a1'],
  },
  'review': {'passed': true, 'findings': []},
  'updated_at': '2026-08-05T00:00:00Z',
};

const _styledResponseJson = {
  'draft': _draftJson,
  'agent_trace': [
    {
      'order': 1,
      'kind': 'tool',
      'label': 'load_style_profile',
      'summary': '读取经验档案',
    },
    {'order': 2, 'kind': 'model', 'label': 'model', 'summary': '完成自评'},
  ],
};

const _fieldSuggestionJson = {
  'suggestion_id': 'suggestion-1',
  'note_id': '11111111-1111-1111-1111-111111111111',
  'field': 'title',
  'value': ['新的标题'],
  'base_field_digest': 'field-digest',
  'base_content_digest': 'content-digest',
  'review': {'passed': true, 'findings': []},
  'evidence': ['睡前哭闹'],
  'evidence_fact_ids': ['source.scenario'],
  'created_at': '2026-08-16T00:00:00Z',
};

RedBookEditorApiClient _client(
  Future<http.Response> Function(http.Request request) handler,
) {
  return RedBookEditorApiClient(
    client: MockClient(handler),
    baseUrl: 'http://test',
  );
}

void main() {
  group('account isolation', () {
    test('generateNoteWithProgress consumes AgentRun SSE events', () async {
      final paths = <String>[];
      final runJson = {
        'run_id': 'run-1',
        'note_id': _draftJson['note_id'],
        'account_id': _accountId,
        'column_id': _columnId,
        'operation': 'generate',
        'form': 'experience',
        'status': 'queued',
        'current_phase': null,
        'attempt': 1,
        'cancel_requested': false,
        'created_at': '2026-08-16T00:00:00Z',
        'updated_at': '2026-08-16T00:00:00Z',
      };
      final client = _client((request) async {
        paths.add(request.url.path);
        if (request.method == 'POST' &&
            request.url.path == '/api/v1/agent-runs') {
          return http.Response(jsonEncode(runJson), 202);
        }
        if (request.url.path.endsWith('/events')) {
          return http.Response.bytes(
            utf8.encode(
              'id: 1\nevent: phase\ndata: ${jsonEncode({'run_id': 'run-1', 'sequence': 1, 'event_type': 'phase', 'phase': 'draft', 'label': 'draft', 'summary': '进入阶段：draft', 'attempt': 1})}\n\n'
              'id: 2\nevent: run.completed\ndata: ${jsonEncode({'run_id': 'run-1', 'sequence': 2, 'event_type': 'run.completed', 'phase': 'safety_review', 'label': 'completed', 'summary': '完成', 'status': 'completed', 'attempt': 1})}\n\n',
            ),
            200,
            headers: {'content-type': 'text/event-stream'},
          );
        }
        if (request.url.path.endsWith('/agent-runs/run-1')) {
          return http.Response(
            jsonEncode({...runJson, 'status': 'completed'}),
            200,
          );
        }
        return http.Response.bytes(utf8.encode(jsonEncode(_draftJson)), 200);
      });
      final events = <AgentRunEvent>[];
      final result = await client.generateNoteWithProgress(
        accountId: _accountId,
        columnId: _columnId,
        source: const SourceExperience(
          babyMonth: 19,
          scenario: '睡前哭闹',
          actions: ['固定绘本时间'],
        ),
        form: StyleForm.experience,
        onEvent: events.add,
      );
      expect(events.first.label, 'draft');
      expect(result.draft.noteId, _draftJson['note_id']);
      expect(paths, [
        '/api/v1/agent-runs',
        '/api/v1/agent-runs/run-1/events',
        '/api/v1/agent-runs/run-1',
        '/api/v1/notes/${_draftJson['note_id']}',
      ]);
    });

    test('generateNote sends account and column ids', () async {
      final requests = <http.Request>[];
      final client = _client((request) async {
        requests.add(request);
        return http.Response(
          jsonEncode(_styledResponseJson),
          200,
          headers: {'content-type': 'application/json'},
        );
      });
      await client.generateNote(
        accountId: _accountId,
        columnId: _columnId,
        source: const SourceExperience(
          babyMonth: 19,
          scenario: '睡前哭闹',
          actions: ['固定绘本时间'],
        ),
        form: StyleForm.experience,
      );
      final body = jsonDecode(requests.single.body) as Map<String, dynamic>;
      expect(body['account_id'], _accountId);
      expect(body['column_id'], _columnId);
      expect(body['form'], 'experience');
    });

    test('generateNote parses styled response with agent trace', () async {
      final client = _client((request) async {
        return http.Response(
          jsonEncode(_styledResponseJson),
          200,
          headers: {'content-type': 'application/json'},
        );
      });
      final result = await client.generateNote(
        accountId: _accountId,
        columnId: _columnId,
        source: const SourceExperience(
          babyMonth: 19,
          scenario: '睡前哭闹',
          actions: ['固定绘本时间'],
        ),
        form: StyleForm.popularScience,
      );
      expect(result.draft.noteId, '11111111-1111-1111-1111-111111111111');
      expect(result.agentTrace, hasLength(2));
      expect(result.agentTrace.first.label, 'load_style_profile');
    });

    test('restyleNote posts draft and form to the style endpoint', () async {
      final requests = <http.Request>[];
      final client = _client((request) async {
        requests.add(request);
        return http.Response(
          jsonEncode(_styledResponseJson),
          200,
          headers: {'content-type': 'application/json'},
        );
      });
      final draft = NoteDraft.fromJson(_draftJson);
      final result = await client.restyleNote(
        draft: draft,
        form: StyleForm.advertorial,
      );
      expect(requests.single.url.path, '/api/v1/notes/style');
      final body = jsonDecode(requests.single.body) as Map<String, dynamic>;
      expect(body['form'], 'advertorial');
      expect((body['draft'] as Map<String, dynamic>)['note_id'], draft.noteId);
      expect(result.agentTrace, isNotEmpty);
    });

    test('listNotes uses the account-scoped path', () async {
      final requests = <http.Request>[];
      final client = _client((request) async {
        requests.add(request);
        return http.Response('[]', 200);
      });
      await client.listNotes(accountId: _accountId);
      expect(requests.single.url.path, '/api/v1/accounts/$_accountId/notes');
    });

    test('uploadAsset and listAssets use the account-scoped path', () async {
      final paths = <String>[];
      final client = _client((request) async {
        paths.add(request.url.path);
        if (request.method == 'POST') {
          return http.Response(
            jsonEncode({'asset_id': 'a1', 'storage_key': 'k'}),
            201,
            headers: {'content-type': 'application/json'},
          );
        }
        return http.Response('[]', 200);
      });
      final file = File(
        '${Directory.systemTemp.path}/red_book_editor_upload_test.jpg',
      );
      await file.writeAsBytes([0xff, 0xd8, 0xff, 0xe0]);
      addTearDown(() => file.deleteSync());
      await client.uploadAsset(accountId: _accountId, filePath: file.path);
      await client.listAssets(accountId: _accountId);
      expect(paths, [
        '/api/v1/accounts/$_accountId/assets',
        '/api/v1/accounts/$_accountId/assets',
      ]);
    });
  });

  group('source-fact preservation', () {
    test('generateNote body carries the exact source facts', () async {
      final requests = <http.Request>[];
      final client = _client((request) async {
        requests.add(request);
        return http.Response(
          jsonEncode(_styledResponseJson),
          200,
          headers: {'content-type': 'application/json'},
        );
      });
      await client.generateNote(
        accountId: _accountId,
        columnId: _columnId,
        source: const SourceExperience(
          babyMonth: 19,
          scenario: '睡前哭闹',
          actions: ['固定绘本时间', '关灯'],
          observations: '入睡过程变顺了一些',
          notes: '补充说明',
          assetIds: ['a1'],
        ),
        form: StyleForm.experience,
      );
      final source =
          jsonDecode(requests.single.body)['source'] as Map<String, dynamic>;
      expect(source['scenario'], '睡前哭闹');
      expect(source['actions'], ['固定绘本时间', '关灯']);
      expect(source['observations'], '入睡过程变顺了一些');
      expect(source['notes'], '补充说明');
      expect(source['asset_ids'], ['a1']);
    });

    test('SourceExperience round-trips notes and asset ids', () {
      final source = SourceExperience(
        babyMonth: 19,
        scenario: '睡前哭闹',
        actions: ['固定绘本时间'],
        observations: '入睡过程变顺了一些',
        notes: '补充说明',
        assetIds: ['a1', 'a2'],
      );
      final restored = SourceExperience.fromJson(
        Map<String, dynamic>.from(source.toJson()),
      );
      expect(restored.notes, '补充说明');
      expect(restored.assetIds, ['a1', 'a2']);
      expect(restored.actions, ['固定绘本时间']);
    });
  });

  group('selective regeneration', () {
    test('regenerateField sends the field and full draft', () async {
      final requests = <http.Request>[];
      final client = _client((request) async {
        requests.add(request);
        return http.Response(
          jsonEncode(_fieldSuggestionJson),
          200,
          headers: {'content-type': 'application/json'},
        );
      });
      final draft = NoteDraft.fromJson(_draftJson);
      final result = await client.regenerateField(
        draft: draft,
        field: 'title',
        form: StyleForm.experience,
      );
      final body = jsonDecode(requests.single.body) as Map<String, dynamic>;
      expect(body['field'], 'title');
      expect(body['form'], 'experience');
      expect((body['draft'] as Map<String, dynamic>)['note_id'], draft.noteId);
      expect(result.field, EditableField.title);
      expect(result.listValue, ['新的标题']);
      expect(result.evidenceFactIds, ['source.scenario']);
    });

    test('regenerateField can rely on the restored draft style form', () async {
      final requests = <http.Request>[];
      final client = _client((request) async {
        requests.add(request);
        return http.Response(
          jsonEncode({
            ..._fieldSuggestionJson,
            'field': 'body',
            'value': '新的正文',
          }),
          200,
          headers: {'content-type': 'application/json'},
        );
      });
      final draft = NoteDraft.fromJson(_draftJson);
      await client.regenerateField(draft: draft, field: 'body');
      final body = jsonDecode(requests.single.body) as Map<String, dynamic>;
      expect(body.containsKey('form'), isFalse);
      expect(
        (body['draft'] as Map<String, dynamic>)['style_form'],
        'experience',
      );
    });

    test('saveNote sends style form metadata', () async {
      final requests = <http.Request>[];
      final client = _client((request) async {
        requests.add(request);
        return http.Response(
          jsonEncode(_draftJson),
          200,
          headers: {'content-type': 'application/json'},
        );
      });
      final draft = NoteDraft.fromJson(_draftJson);
      await client.saveNote(draft: draft);
      final body = jsonDecode(requests.single.body) as Map<String, dynamic>;
      expect(body['style_form'], 'experience');
    });

    test('NoteDraft round-trips style form through JSON and copyWith', () {
      final draft = NoteDraft.fromJson(_draftJson);
      expect(draft.styleForm, StyleForm.experience);
      expect(
        draft.copyWith(styleForm: StyleForm.advertorial).styleForm,
        StyleForm.advertorial,
      );
      expect(draft.toJson()['style_form'], 'experience');
    });

    test('NoteDraft parses claim audit evidence and support state', () {
      final payload = Map<String, dynamic>.from(_draftJson);
      payload['review'] = {
        'passed': true,
        'findings': [],
        'claim_audit': [
          {
            'field': 'body',
            'claim': '固定绘本时间',
            'support': 'supported',
            'evidence_fact_ids': ['source.actions[0]'],
            'evidence': ['固定绘本时间'],
            'reason': '',
            'level': 'none',
          },
        ],
        'source_digest': 'source-digest',
        'content_digest': 'content-digest',
        'audit_version': 'fact-ledger-v1',
        'policy_version': 'parenting-safety-v1',
      };
      final draft = NoteDraft.fromJson(payload);

      expect(draft.review, isNotNull);
      expect(draft.review!.claimAudit.single.support, ClaimSupport.supported);
      expect(draft.review!.claimAudit.single.evidence, ['固定绘本时间']);
      expect(
        (draft.toJson()['review'] as Map<String, dynamic>)['content_digest'],
        'content-digest',
      );
    });

    test(
      'FieldSuggestion round-trips target values and review field metadata',
      () {
        final suggestion = FieldSuggestion.fromJson(_fieldSuggestionJson);
        expect(suggestion.field, EditableField.title);
        expect(suggestion.listValue, ['新的标题']);
        expect(suggestion.review, isNotNull);
        expect(suggestion.toJson()['field'], 'title');
      },
    );

    test('ReviewFinding keeps optional field metadata for legacy payloads', () {
      final payload = Map<String, dynamic>.from(_draftJson);
      payload['review'] = {
        'passed': false,
        'findings': [
          {
            'level': 'blocking',
            'code': 'medication',
            'message': '不能提供用药建议',
            'field': 'body',
            'matched_text': '吃什么药',
          },
        ],
      };
      final draft = NoteDraft.fromJson(payload);
      expect(draft.review!.findings.single.field, 'body');
      expect(draft.review!.findings.single.matchedText, '吃什么药');
    });
  });

  group('agent recovery', () {
    test(
      'SSE reconnect cursor starts after the last received sequence',
      () async {
        final requests = <http.Request>[];
        final client = _client((request) async {
          requests.add(request);
          return http.Response.bytes(
            utf8.encode(
              'id: 4\nevent: run.completed\ndata: ${jsonEncode({'run_id': 'run-1', 'sequence': 4, 'event_type': 'run.completed', 'phase': 'safety_review', 'label': 'completed', 'summary': '完成', 'status': 'completed', 'attempt': 1})}\n\n',
            ),
            200,
            headers: {'content-type': 'text/event-stream'},
          );
        });

        final events = await client
            .watchAgentRunEvents(runId: 'run-1', after: 3)
            .toList();
        expect(events.single.sequence, 4);
        expect(requests.single.url.queryParameters['after'], '3');
      },
    );

    test('resume failure never opens a failed run as an editable note', () async {
      final runJson = {
        'run_id': 'run-1',
        'note_id': '11111111-1111-1111-1111-111111111111',
        'account_id': _accountId,
        'column_id': _columnId,
        'operation': 'generate',
        'form': 'experience',
        'status': 'queued',
        'current_phase': null,
        'attempt': 1,
        'cancel_requested': false,
        'created_at': '2026-08-16T00:00:00Z',
        'updated_at': '2026-08-16T00:00:00Z',
      };
      final paths = <String>[];
      final client = _client((request) async {
        paths.add(request.url.path);
        if (request.url.path.endsWith('/resume')) {
          return http.Response(jsonEncode(runJson), 202);
        }
        if (request.url.path.endsWith('/events')) {
          return http.Response.bytes(
            utf8.encode(
              'id: 1\nevent: run.failed\ndata: ${jsonEncode({'run_id': 'run-1', 'sequence': 1, 'event_type': 'run.failed', 'phase': 'model', 'label': 'failed', 'summary': '失败', 'status': 'failed', 'attempt': 1})}\n\n',
            ),
            200,
          );
        }
        return http.Response(jsonEncode({...runJson, 'status': 'failed'}), 200);
      });

      await expectLater(
        client.resumeAgentRunWithProgress(runId: 'run-1'),
        throwsA(isA<ApiRequestException>()),
      );
      expect(paths, contains('/api/v1/agent-runs/run-1/resume'));
      expect(
        paths,
        isNot(contains('/api/v1/notes/11111111-1111-1111-1111-111111111111')),
      );
    });
  });

  group('manual publishing boundary', () {
    test('recordPublication only posts the publish-record endpoint', () async {
      final requests = <http.Request>[];
      final client = _client((request) async {
        requests.add(request);
        return http.Response(
          jsonEncode({
            'note_id': '11111111-1111-1111-1111-111111111111',
            'status': 'published',
            'link': 'https://example.com/note',
            'views': 10,
          }),
          201,
          headers: {'content-type': 'application/json'},
        );
      });
      await client.recordPublication(
        noteId: '11111111-1111-1111-1111-111111111111',
        status: 'published',
        link: 'https://example.com/note',
        views: 10,
      );
      final request = requests.single;
      expect(
        request.url.path,
        '/api/v1/notes/11111111-1111-1111-1111-111111111111/publish-record',
      );
      final body = jsonDecode(request.body) as Map<String, dynamic>;
      expect(body.keys, containsAll(['status', 'link', 'views']));
      expect(body.containsKey('access_token'), isFalse);
      expect(body.containsKey('xhs_credential'), isFalse);
    });

    test('NoteDraft ignores any returned publish credentials', () {
      final payload = Map<String, dynamic>.from(_draftJson);
      payload['access_token'] = 'secret';
      payload['xhs_credential'] = 'secret';
      final draft = NoteDraft.fromJson(payload);
      expect(draft.noteId, '11111111-1111-1111-1111-111111111111');
    });
  });
}
