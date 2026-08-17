import 'package:flutter_test/flutter_test.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:red_book_editor/main.dart';

void main() {
  testWidgets('renders the workbench shell', (WidgetTester tester) async {
    await tester.pumpWidget(const RedBookEditorApp());
    expect(find.text('小红书内容工作台'), findsOneWidget);
  });

  testWidgets('empty accounts have a first-use setup action', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [accountsProvider.overrideWith((ref) async => const [])],
        child: const MaterialApp(home: WorkbenchHomePage()),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('配置第一个账号'), findsOneWidget);
    expect(find.textContaining('无需注册或登录'), findsOneWidget);
  });
}
