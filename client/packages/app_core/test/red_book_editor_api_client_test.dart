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
        final regenerated = Map<String, dynamic>.from(_draftJson);
        regenerated['title_candidates'] = ['新的标题'];
        return http.Response(
          jsonEncode(regenerated),
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
      expect(result.titleCandidates, ['新的标题']);
      expect(result.body, '宝宝19个月时，遇到了睡前哭闹。');
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
