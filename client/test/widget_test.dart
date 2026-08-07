import 'package:flutter_test/flutter_test.dart';
import 'package:red_book_editor/main.dart';

void main() {
  testWidgets('renders the workbench shell', (WidgetTester tester) async {
    await tester.pumpWidget(const RedBookEditorApp());
    expect(find.text('小红书内容工作台'), findsOneWidget);
  });
}
