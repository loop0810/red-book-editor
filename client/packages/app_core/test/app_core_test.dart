import 'package:app_core/app_core.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences_platform_interface/in_memory_shared_preferences_async.dart';
import 'package:shared_preferences_platform_interface/shared_preferences_async_platform_interface.dart';

void main() {
  setUp(() {
    SharedPreferencesAsyncPlatform.instance =
        InMemorySharedPreferencesAsync.empty();
  });

  test('uses the local development API by default', () {
    final client = RedBookEditorApiClient();
    expect(client.baseUrl, 'http://127.0.0.1:8100');
  });

  test('StyleForm maps to api values', () {
    expect(styleFormToApi(StyleForm.popularScience), 'popular_science');
    expect(styleFormToApi(StyleForm.experience), 'experience');
    expect(styleFormToApi(StyleForm.advertorial), 'advertorial');
    expect(styleFormFromApi('popular_science'), StyleForm.popularScience);
    expect(styleFormFromApi('advertorial'), StyleForm.advertorial);
    expect(styleFormDisplayName(StyleForm.popularScience), '科普');
  });

  test('StyledNoteResponse parses draft and agent trace', () {
    final response = StyledNoteResponse.fromJson({
      'draft': {
        'note_id': '11111111-1111-1111-1111-111111111111',
        'account_id': '00000000-0000-0000-0000-000000000001',
        'column_id': '00000000-0000-0000-0000-000000000002',
        'status': 'ready',
        'source': {
          'baby_month': 19,
          'scenario': '睡前哭闹',
          'actions': ['固定绘本时间'],
        },
      },
      'agent_trace': [
        {
          'order': 1,
          'kind': 'tool',
          'label': 'critique_draft',
          'summary': 'scores ok',
          'phase': 'critique',
        },
      ],
    });
    expect(response.draft.noteId, '11111111-1111-1111-1111-111111111111');
    expect(response.agentTrace.single.label, 'critique_draft');
    expect(response.agentTrace.single.order, 1);
    expect(response.agentTrace.single.phase, 'critique');
  });

  test('StyledNoteResponse accepts the public result projection', () {
    final response = StyledNoteResponse.fromJson({
      'draft': {
        'note_id': '11111111-1111-1111-1111-111111111111',
        'account_id': '00000000-0000-0000-0000-000000000001',
        'column_id': '00000000-0000-0000-0000-000000000002',
        'status': 'ready',
        'domain_id': 'parenting',
        'content_brief': {
          'focus': '宝宝周岁宴',
          'raw_material': '不办大型酒宴，只和家人吃顿饭。',
          'domain_context': {'baby_month': 12},
        },
        'focus': '宝宝周岁宴',
        'title_candidates': ['宝宝周岁宴：和家人吃顿饭'],
        'body': '记录这次简单的周岁宴。',
        'hashtags': ['#周岁宴'],
        'image_suggestions': ['家庭合照'],
        'updated_at': '2026-08-16T00:00:00Z',
      },
      'issues': [],
    });

    expect(response.draft.focus, '宝宝周岁宴');
    expect(response.draft.review, isNull);
    expect(response.agentTrace, isEmpty);
  });

  test(
    'ContentBrief draft storage preserves rough material for recovery',
    () async {
      final store = ContentBriefDraftStore();
      const brief = ContentBrief(
        focus: '宝宝周岁宴',
        rawMaterial: '周岁，父母，晚餐，大家开心',
        domainContext: {'baby_month': 12},
      );

      await store.save(brief);
      final restored = await store.load();

      expect(restored?.focus, brief.focus);
      expect(restored?.rawMaterial, brief.rawMaterial);
      expect(restored?.domainContext['baby_month'], 12);
    },
  );
}
