import 'package:app_core/app_core.dart';
import 'package:flutter_test/flutter_test.dart';

NoteDraft _draft({String title = '原标题', String body = '第一段。'}) {
  return NoteDraft(
    noteId: 'note-1',
    accountId: 'account-1',
    columnId: 'column-1',
    status: NoteStatus.ready,
    source: const SourceExperience(
      babyMonth: 19,
      scenario: '睡前哭闹',
      actions: ['固定绘本时间'],
    ),
    titleCandidates: [title],
    body: body,
    hashtags: const ['#育儿'],
    coverCopy: '睡前记录',
  );
}

FieldSuggestion _suggestion({
  EditableField field = EditableField.title,
  Object value = const ['新标题'],
}) {
  return FieldSuggestion(
    suggestionId: 'suggestion-1',
    noteId: 'note-1',
    field: field,
    value: value,
    baseFieldDigest: 'base-field',
    baseContentDigest: 'base-content',
    evidence: const ['睡前哭闹'],
    evidenceFactIds: const ['source.scenario'],
  );
}

void main() {
  test('body diff keeps sentence boundaries and hashtag diff is set based', () {
    final bodyDiff = diffFieldValues(
      field: EditableField.body,
      before: '第一段。第二段。',
      after: '第一段。新的第二段。',
    );
    expect(
      bodyDiff.segments.map((segment) => segment.kind),
      contains(DiffSegmentKind.removed),
    );
    expect(
      bodyDiff.segments.map((segment) => segment.kind),
      contains(DiffSegmentKind.added),
    );

    final hashtagDiff = diffFieldValues(
      field: EditableField.hashtags,
      before: const ['#育儿', '#睡眠'],
      after: const ['#睡眠', '#记录'],
    );
    expect(
      hashtagDiff.segments.map((segment) => segment.text).join(),
      contains('#记录'),
    );
    expect(
      hashtagDiff.segments.map((segment) => segment.text).join(),
      contains('#育儿'),
    );
  });

  test('accept only changes the target field and preserves the rest', () {
    final session = EditorSessionState(
      draft: _draft(),
    ).addSuggestion(_suggestion(), baseValue: const ['原标题']);
    final accepted = session.acceptSuggestion(
      session.pendingSuggestions.single,
    );
    expect(accepted.draft.titleCandidates, ['新标题']);
    expect(accepted.draft.body, '第一段。');
    expect(accepted.draft.hashtags, ['#育儿']);
    expect(accepted.pendingSuggestions, isEmpty);
  });

  test('manual edits make a pending suggestion conflicted', () {
    final session = EditorSessionState(
      draft: _draft(title: '用户标题'),
      aiBaseline: const {
        EditableField.title: ['原标题'],
      },
    ).addSuggestion(_suggestion(), baseValue: const ['原标题']);
    final suggestion = session.pendingSuggestions.single;
    expect(session.hasConflict(suggestion), isTrue);
    expect(session.acceptSuggestion(suggestion).draft.titleCandidates, [
      '用户标题',
    ]);
    expect(
      session.acceptSuggestion(suggestion, force: true).draft.titleCandidates,
      ['新标题'],
    );
    expect(session.hasDirtyFields, isTrue);
    expect(session.hasConflicts, isTrue);
  });
}
