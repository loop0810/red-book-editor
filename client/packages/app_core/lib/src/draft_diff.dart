import 'content_workflow_models.dart';

enum DiffSegmentKind { unchanged, added, removed }

class DiffSegment {
  const DiffSegment({required this.kind, required this.text});

  final DiffSegmentKind kind;
  final String text;
}

class FieldDiff {
  const FieldDiff({required this.segments});

  final List<DiffSegment> segments;

  bool get hasChanges =>
      segments.any((segment) => segment.kind != DiffSegmentKind.unchanged);
}

FieldDiff diffFieldValues({
  required EditableField field,
  required Object? before,
  required Object? after,
}) {
  final beforeTokens = _tokens(field, before);
  final afterTokens = _tokens(field, after);
  return FieldDiff(segments: _diffTokens(beforeTokens, afterTokens));
}

List<String> _tokens(EditableField field, Object? value) {
  if (value is List<dynamic>) {
    final values = value.cast<String>();
    if (field == EditableField.hashtags) {
      return values.toSet().toList()..sort();
    }
    return values;
  }
  final text = value?.toString() ?? '';
  if (field == EditableField.body) {
    return text
        .split(RegExp(r'(?<=[。！？!?；;])|\n'))
        .where((token) => token.isNotEmpty)
        .toList();
  }
  if (field == EditableField.title || field == EditableField.coverCopy) {
    return text.runes.map(String.fromCharCode).toList();
  }
  if (field == EditableField.hashtags) {
    return text
        .split(RegExp(r'\s+'))
        .where((token) => token.isNotEmpty)
        .toSet()
        .toList()
      ..sort();
  }
  return text.split(RegExp(r'\s+')).where((token) => token.isNotEmpty).toList();
}

List<DiffSegment> _diffTokens(List<String> before, List<String> after) {
  final rows = before.length + 1;
  final columns = after.length + 1;
  final lcs = List.generate(rows, (_) => List.filled(columns, 0));
  for (var row = before.length - 1; row >= 0; row--) {
    for (var column = after.length - 1; column >= 0; column--) {
      lcs[row][column] = before[row] == after[column]
          ? lcs[row + 1][column + 1] + 1
          : lcs[row + 1][column] > lcs[row][column + 1]
          ? lcs[row + 1][column]
          : lcs[row][column + 1];
    }
  }

  final segments = <DiffSegment>[];
  void add(DiffSegmentKind kind, String token) {
    if (token.isEmpty) return;
    if (segments.isNotEmpty && segments.last.kind == kind) {
      final previous = segments.removeLast();
      segments.add(DiffSegment(kind: kind, text: '${previous.text}$token'));
    } else {
      segments.add(DiffSegment(kind: kind, text: token));
    }
  }

  var row = 0;
  var column = 0;
  while (row < before.length && column < after.length) {
    if (before[row] == after[column]) {
      add(DiffSegmentKind.unchanged, before[row]);
      row++;
      column++;
    } else if (lcs[row + 1][column] >= lcs[row][column + 1]) {
      add(DiffSegmentKind.removed, before[row]);
      row++;
    } else {
      add(DiffSegmentKind.added, after[column]);
      column++;
    }
  }
  while (row < before.length) {
    add(DiffSegmentKind.removed, before[row++]);
  }
  while (column < after.length) {
    add(DiffSegmentKind.added, after[column++]);
  }
  return segments;
}
