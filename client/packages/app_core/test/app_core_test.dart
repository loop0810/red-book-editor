import 'package:app_core/app_core.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('uses the local development API by default', () {
    final client = RedBookEditorApiClient();
    expect(client.baseUrl, 'http://127.0.0.1:8000');
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
        },
      ],
    });
    expect(response.draft.noteId, '11111111-1111-1111-1111-111111111111');
    expect(response.agentTrace.single.label, 'critique_draft');
    expect(response.agentTrace.single.order, 1);
  });
}
