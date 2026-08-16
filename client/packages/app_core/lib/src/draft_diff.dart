import 'content_workflow_models.dart';

enum DiffSegmentKind { unchanged, added, removed }

class DiffSegment {
  const DiffSegment({
    required this.kind,
    required this.text,
    this.beforeStart,
    this.beforeEnd,
    this.afterStart,
    this.afterEnd,
  });

  final DiffSegmentKind kind;
  final String text;

  /// Ranges use Dart/Flutter UTF-16 code-unit offsets. Hashtag set diffs have
  /// no text range because their order is intentionally normalized.
  final int? beforeStart;
  final int? beforeEnd;
  final int? afterStart;
  final int? afterEnd;
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

class _DiffToken {
  const _DiffToken(this.text, {this.start, this.end});

  final String text;
  final int? start;
  final int? end;
}

List<_DiffToken> _tokens(EditableField field, Object? value) {
  if (value is List<dynamic>) {
    final values = value.cast<String>();
    final normalized = field == EditableField.hashtags
        ? (values.toSet().toList()..sort())
        : values;
    return normalized.map(_DiffToken.new).toList();
  }
  final text = value?.toString() ?? '';
  if (field == EditableField.body) return _bodyTokens(text);
  if (field == EditableField.title || field == EditableField.coverCopy) {
    return _characterTokens(text);
  }
  return _wordTokens(text);
}

List<_DiffToken> _bodyTokens(String text) {
  final tokens = <_DiffToken>[];
  var start = 0;
  var offset = 0;
  for (final rune in text.runes) {
    final character = String.fromCharCode(rune);
    offset += character.length;
    if ('。！？!?；;\n'.contains(character)) {
      if (offset > start) {
        tokens.add(
          _DiffToken(text.substring(start, offset), start: start, end: offset),
        );
      }
      start = offset;
    }
  }
  if (start < text.length) {
    tokens.add(
      _DiffToken(text.substring(start), start: start, end: text.length),
    );
  }
  return tokens;
}

List<_DiffToken> _characterTokens(String text) {
  final tokens = <_DiffToken>[];
  var offset = 0;
  for (final rune in text.runes) {
    final character = String.fromCharCode(rune);
    final end = offset + character.length;
    tokens.add(_DiffToken(character, start: offset, end: end));
    offset = end;
  }
  return tokens;
}

List<_DiffToken> _wordTokens(String text) {
  final tokens = <_DiffToken>[];
  for (final match in RegExp(r'\S+').allMatches(text)) {
    tokens.add(_DiffToken(match.group(0)!, start: match.start, end: match.end));
  }
  return tokens;
}

List<DiffSegment> _diffTokens(List<_DiffToken> before, List<_DiffToken> after) {
  final rows = before.length + 1;
  final columns = after.length + 1;
  final lcs = List.generate(rows, (_) => List.filled(columns, 0));
  for (var row = before.length - 1; row >= 0; row--) {
    for (var column = after.length - 1; column >= 0; column--) {
      lcs[row][column] = before[row].text == after[column].text
          ? lcs[row + 1][column + 1] + 1
          : lcs[row + 1][column] > lcs[row][column + 1]
          ? lcs[row + 1][column]
          : lcs[row][column + 1];
    }
  }

  final segments = <DiffSegment>[];
  void add(DiffSegmentKind kind, _DiffToken token, {bool isBefore = false}) {
    if (token.text.isEmpty) return;
    final beforeStart = isBefore ? token.start : null;
    final beforeEnd = isBefore ? token.end : null;
    final afterStart = isBefore ? null : token.start;
    final afterEnd = isBefore ? null : token.end;
    if (segments.isNotEmpty && segments.last.kind == kind) {
      final previous = segments.removeLast();
      segments.add(
        DiffSegment(
          kind: kind,
          text: '${previous.text}${token.text}',
          beforeStart: previous.beforeStart ?? beforeStart,
          beforeEnd: beforeEnd ?? previous.beforeEnd,
          afterStart: previous.afterStart ?? afterStart,
          afterEnd: afterEnd ?? previous.afterEnd,
        ),
      );
    } else {
      segments.add(
        DiffSegment(
          kind: kind,
          text: token.text,
          beforeStart: beforeStart,
          beforeEnd: beforeEnd,
          afterStart: afterStart,
          afterEnd: afterEnd,
        ),
      );
    }
  }

  var row = 0;
  var column = 0;
  while (row < before.length && column < after.length) {
    if (before[row].text == after[column].text) {
      final left = before[row];
      final right = after[column];
      segments.add(
        DiffSegment(
          kind: DiffSegmentKind.unchanged,
          text: left.text,
          beforeStart: left.start,
          beforeEnd: left.end,
          afterStart: right.start,
          afterEnd: right.end,
        ),
      );
      row++;
      column++;
    } else if (lcs[row + 1][column] >= lcs[row][column + 1]) {
      add(DiffSegmentKind.removed, before[row++], isBefore: true);
    } else {
      add(DiffSegmentKind.added, after[column++]);
    }
  }
  while (row < before.length) {
    add(DiffSegmentKind.removed, before[row++], isBefore: true);
  }
  while (column < after.length) {
    add(DiffSegmentKind.added, after[column++]);
  }
  return segments;
}
