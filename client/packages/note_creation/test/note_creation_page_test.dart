import 'package:app_core/app_core.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:note_creation/note_creation.dart';
import 'package:shared_preferences_platform_interface/in_memory_shared_preferences_async.dart';
import 'package:shared_preferences_platform_interface/shared_preferences_async_platform_interface.dart';

NoteDraft _draft() {
  return const NoteDraft(
    noteId: '11111111-1111-1111-1111-111111111111',
    accountId: '00000000-0000-0000-0000-000000000001',
    columnId: '00000000-0000-0000-0000-000000000002',
    status: NoteStatus.ready,
    source: SourceExperience(
      babyMonth: 19,
      scenario: '睡前哭闹',
      actions: ['固定绘本时间'],
    ),
    titleCandidates: ['原标题'],
    body: '宝宝19个月时，遇到了睡前哭闹。',
  );
}

void main() {
  setUp(() {
    SharedPreferencesAsyncPlatform.instance =
        InMemorySharedPreferencesAsync.empty();
  });

  testWidgets(
    'primary creation page is content-first and hides internal audit',
    (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: NoteCreationPage(
            generate: (brief, form) async =>
                StyledNoteResponse(draft: _draft()),
          ),
        ),
      );

      expect(find.text('标题'), findsOneWidget);
      expect(find.text('正文'), findsOneWidget);
      expect(find.widgetWithText(TextField, '内容主题'), findsOneWidget);
      expect(find.widgetWithText(TextField, '原始正文'), findsOneWidget);
      expect(find.text('发生了什么'), findsNothing);
      expect(find.text('我做了什么（可用逗号分隔）'), findsNothing);
      expect(find.text('观察到什么变化'), findsNothing);
      expect(find.text('Agent 执行过程'), findsNothing);
      expect(find.textContaining('来源证据'), findsNothing);
    },
  );

  testWidgets('form selector passes the chosen expression form', (
    tester,
  ) async {
    StyleForm? receivedForm;
    await tester.pumpWidget(
      MaterialApp(
        home: NoteCreationPage(
          generate: (source, form) async {
            receivedForm = form;
            return StyledNoteResponse(draft: _draft(), agentTrace: const []);
          },
          onDraftGenerated: (response, form) async {
            receivedForm = form;
          },
        ),
      ),
    );

    await tester.enterText(find.widgetWithText(TextField, '内容主题'), '宝宝半夜发烧');
    await tester.enterText(
      find.widgetWithText(TextField, '原始正文'),
      '宝宝半夜发烧，我记录了体温并陪着照顾。',
    );
    await tester.scrollUntilVisible(
      find.text('科普'),
      200,
      scrollable: find.byType(Scrollable).first,
    );
    expect(find.text('科普'), findsOneWidget);
    expect(find.text('经验'), findsOneWidget);
    expect(find.text('软文'), findsOneWidget);
    await tester.tap(find.text('软文'));
    await tester.pump();
    await tester.scrollUntilVisible(
      find.text('生成笔记'),
      200,
      scrollable: find.byType(Scrollable).first,
    );
    await tester.ensureVisible(find.byType(FilledButton).last);
    await tester.tap(find.byType(FilledButton).last);
    await tester.pump();

    expect(receivedForm, StyleForm.advertorial);
  });

  testWidgets('note editor hides internal agent trace', (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        home: NoteEditorPage(
          draft: _draft(),
          agentTrace: const [
            AgentTraceStep(
              order: 1,
              kind: 'tool',
              label: 'load_style_profile',
              summary: '读取经验档案',
            ),
            AgentTraceStep(
              order: 2,
              kind: 'model',
              label: 'model',
              summary: '完成自评',
            ),
          ],
        ),
      ),
    );

    expect(find.text('Agent 执行过程'), findsNothing);
    expect(find.text('读取风格档案'), findsNothing);
    expect(find.text('模型思考'), findsNothing);
  });

  testWidgets('field candidate stays pending until explicit accept', (
    tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        home: NoteEditorPage(
          draft: _draft(),
          aiBaseline: _draft(),
          onRegenerateField: (draft, field, {form}) async => FieldSuggestion(
            suggestionId: 'suggestion-1',
            noteId: draft.noteId,
            field: EditableField.title,
            value: const ['AI 标题'],
            baseFieldDigest: 'field-digest',
            baseContentDigest: 'content-digest',
            evidence: const ['睡前哭闹'],
            evidenceFactIds: const ['source.scenario'],
          ),
        ),
      ),
    );

    await tester.tap(find.text('重新生成标题'));
    await tester.pumpAndSettle();
    final titleField = tester.widget<TextField>(find.byType(TextField).first);
    expect(titleField.controller!.text, '原标题');
    expect(find.text('AI 标题候选'), findsOneWidget);
    expect(find.text('来源证据：睡前哭闹、source.scenario'), findsOneWidget);

    await tester.tap(find.text('采纳'));
    await tester.pumpAndSettle();
    expect(
      tester.widget<TextField>(find.byType(TextField).first).controller!.text,
      'AI 标题',
    );
    expect(find.text('AI 标题候选'), findsNothing);
  });

  testWidgets(
    'restores suggestion history and keeps resolved candidates read-only',
    (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: NoteEditorPage(
            draft: _draft(),
            loadSuggestions: (noteId) async => [
              FieldSuggestion(
                suggestionId: 'suggestion-old',
                noteId: noteId,
                field: EditableField.title,
                value: const ['旧候选'],
                baseFieldDigest: 'field-digest',
                baseContentDigest: 'content-digest',
                status: SuggestionStatus.accepted,
                createdAt: '2026-08-16T00:00:00Z',
              ),
              FieldSuggestion(
                suggestionId: 'suggestion-new',
                noteId: noteId,
                field: EditableField.title,
                value: const ['新候选'],
                baseFieldDigest: 'field-digest',
                baseContentDigest: 'content-digest',
                createdAt: '2026-08-17T00:00:00Z',
              ),
            ],
          ),
        ),
      );
      await tester.pumpAndSettle();
      expect(find.text('AI 标题候选'), findsOneWidget);
      expect(find.text('标题候选历史'), findsOneWidget);
      await tester.tap(find.text('标题候选历史'));
      await tester.pumpAndSettle();
      expect(find.text('已采纳'), findsOneWidget);
      expect(find.text('待处理'), findsOneWidget);
      expect(find.text('采纳'), findsOneWidget);
    },
  );

  testWidgets('manual edit shows baseline diff and conflict choice', (
    tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        home: NoteEditorPage(
          draft: _draft(),
          aiBaseline: _draft(),
          onRegenerateField: (draft, field, {form}) async => FieldSuggestion(
            suggestionId: 'suggestion-1',
            noteId: draft.noteId,
            field: EditableField.title,
            value: const ['AI 标题'],
            baseFieldDigest: 'field-digest',
            baseContentDigest: 'content-digest',
          ),
        ),
      ),
    );

    await tester.tap(find.text('重新生成标题'));
    await tester.pumpAndSettle();
    await tester.enterText(find.byType(TextField).first, '用户标题');
    await tester.pump();
    expect(find.text('查看 AI 初稿与当前编辑 Diff'), findsOneWidget);
    await tester.tap(find.text('采纳'));
    await tester.pumpAndSettle();
    expect(
      tester.widget<TextField>(find.byType(TextField).first).controller!.text,
      '用户标题',
    );
    await tester.tap(find.text('使用 AI 候选'));
    await tester.pumpAndSettle();
    expect(
      tester.widget<TextField>(find.byType(TextField).first).controller!.text,
      'AI 标题',
    );
  });

  testWidgets('review finding displays matched text and navigates by field', (
    tester,
  ) async {
    final draft = NoteDraft(
      noteId: _draft().noteId,
      accountId: _draft().accountId,
      columnId: _draft().columnId,
      status: NoteStatus.needsReview,
      source: _draft().source,
      titleCandidates: const ['原标题'],
      body: '宝宝应该吃什么药？',
      userIssue: const UserFacingIssue(
        category: 'safety',
        message: '这段内容涉及用药建议，暂不能复制或导出。',
        field: 'body',
        action: '请删除药物、剂量或疗程建议',
      ),
    );
    await tester.pumpWidget(MaterialApp(home: NoteEditorPage(draft: draft)));

    await tester.scrollUntilVisible(
      find.text('这段内容涉及用药建议，暂不能复制或导出。'),
      300,
      scrollable: find.byType(Scrollable).first,
    );
    expect(find.text('请删除药物、剂量或疗程建议'), findsOneWidget);
  });

  testWidgets('failed generation keeps the run available for resume', (
    tester,
  ) async {
    var resumedRunId = '';
    var finished = false;
    var firstAttempt = true;
    var generationCalled = false;
    var runCreated = false;
    final run = AgentRun.fromJson({
      'run_id': 'run-recover-1',
      'note_id': _draft().noteId,
      'account_id': _draft().accountId,
      'column_id': _draft().columnId,
      'operation': 'generate',
      'form': 'experience',
      'status': 'running',
      'attempt': 1,
      'cancel_requested': false,
      'created_at': '2026-08-16T00:00:00Z',
      'updated_at': '2026-08-16T00:00:00Z',
    });
    await tester.pumpWidget(
      MaterialApp(
        home: NoteCreationPage(
          generate: (source, form) async =>
              StyledNoteResponse(draft: _draft(), agentTrace: const []),
          generateWithProgress: (source, form, {onEvent, onRunCreated}) async {
            generationCalled = true;
            if (firstAttempt) {
              firstAttempt = false;
              runCreated = true;
              onRunCreated?.call(run);
              throw StateError('network interrupted');
            }
            return StyledNoteResponse(draft: _draft(), agentTrace: const []);
          },
          resumeAgentRun: (runId, {onEvent, onRunCreated}) async {
            resumedRunId = runId;
            return StyledNoteResponse(draft: _draft(), agentTrace: const []);
          },
          onDraftGenerated: (response, form) async {
            finished = true;
          },
        ),
      ),
    );
    await tester.enterText(find.widgetWithText(TextField, '内容主题'), '半夜醒来');
    await tester.enterText(
      find.widgetWithText(TextField, '原始正文'),
      '我记录了固定安抚流程。',
    );
    await tester.scrollUntilVisible(
      find.text('生成笔记'),
      300,
      scrollable: find.byType(Scrollable).first,
    );
    await tester.drag(find.byType(ListView).first, const Offset(0, -180));
    await tester.pump();
    await tester.tap(find.text('生成笔记'));
    await tester.pumpAndSettle();
    expect(generationCalled, isTrue);
    expect(runCreated, isTrue);
    await tester.scrollUntilVisible(
      find.text('继续运行'),
      300,
      scrollable: find.byType(Scrollable).first,
    );
    expect(find.text('继续运行'), findsOneWidget);

    await tester.tap(find.text('继续运行'));
    await tester.pumpAndSettle();
    expect(resumedRunId, 'run-recover-1');
    expect(finished, isTrue);
  });
}
