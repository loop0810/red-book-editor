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
    body: '宝宝19个月时，遇到了睡前哭闹。',
  );
}

void main() {
  setUp(() {
    SharedPreferencesAsyncPlatform.instance =
        InMemorySharedPreferencesAsync.empty();
  });

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

    await tester.enterText(find.widgetWithText(TextField, '发生了什么'), '宝宝半夜发烧');
    await tester.enterText(
      find.widgetWithText(TextField, '我做了什么（可用逗号分隔）'),
      '温水擦身',
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
    await tester.tap(find.text('生成笔记'));
    await tester.pump();

    expect(receivedForm, StyleForm.advertorial);
  });

  testWidgets('note editor shows agent trace steps', (tester) async {
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

    expect(find.text('Agent 执行过程'), findsOneWidget);
    await tester.tap(find.text('Agent 执行过程'));
    await tester.pumpAndSettle();
    expect(find.text('1. 读取风格档案'), findsOneWidget);
    expect(find.text('2. 模型思考'), findsOneWidget);
  });
}
