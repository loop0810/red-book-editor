import 'content_workflow_models.dart';

Object fieldValueForDraft(NoteDraft draft, EditableField field) {
  switch (field) {
    case EditableField.title:
      return draft.titleCandidates;
    case EditableField.body:
      return draft.body;
    case EditableField.hashtags:
      return draft.hashtags;
    case EditableField.coverCopy:
      return draft.coverCopy;
  }
}

class EditorSessionState {
  const EditorSessionState({
    required this.draft,
    this.aiBaseline = const {},
    this.pendingSuggestions = const [],
  });

  final NoteDraft draft;
  final Map<EditableField, Object> aiBaseline;
  final List<FieldSuggestion> pendingSuggestions;

  FieldSuggestion? suggestionFor(EditableField field) {
    for (final suggestion in suggestionsFor(field)) {
      if (suggestion.status == SuggestionStatus.pending) return suggestion;
    }
    return null;
  }

  List<FieldSuggestion> suggestionsFor(EditableField field) =>
      pendingSuggestions
          .where((suggestion) => suggestion.field == field)
          .toList()
        ..sort((left, right) => right.createdAt.compareTo(left.createdAt));

  bool isDirty(EditableField field) {
    final baseline = aiBaseline[field];
    return baseline != null &&
        !_sameValue(fieldValueForDraft(draft, field), baseline);
  }

  bool get hasDirtyFields => EditableField.values.any(isDirty);

  bool get hasConflicts => pendingSuggestions.any(
    (suggestion) =>
        suggestion.status == SuggestionStatus.pending &&
        hasConflict(suggestion),
  );

  bool hasConflict(FieldSuggestion suggestion) {
    final baseValue = suggestion.baseValue;
    if (baseValue == null) return false;
    return !_sameValue(fieldValueForDraft(draft, suggestion.field), baseValue);
  }

  EditorSessionState addSuggestion(
    FieldSuggestion suggestion, {
    required Object baseValue,
  }) {
    final withBase = suggestion.copyWith(baseValue: baseValue);
    return EditorSessionState(
      draft: draft,
      aiBaseline: aiBaseline,
      pendingSuggestions: [
        ...pendingSuggestions.where(
          (item) => item.suggestionId != suggestion.suggestionId,
        ),
        withBase,
      ],
    );
  }

  EditorSessionState acceptSuggestion(
    FieldSuggestion suggestion, {
    bool force = false,
  }) {
    if (suggestion.status != SuggestionStatus.pending) return this;
    if (!force && hasConflict(suggestion)) return this;
    final updated = _applyValue(draft, suggestion.field, suggestion.value);
    return EditorSessionState(
      draft: updated,
      aiBaseline: aiBaseline,
      pendingSuggestions: pendingSuggestions
          .map(
            (item) => item.suggestionId == suggestion.suggestionId
                ? item.copyWith(status: SuggestionStatus.accepted)
                : item,
          )
          .toList(),
    );
  }

  EditorSessionState rejectSuggestion(FieldSuggestion suggestion) {
    if (suggestion.status != SuggestionStatus.pending) return this;
    return EditorSessionState(
      draft: draft,
      aiBaseline: aiBaseline,
      pendingSuggestions: pendingSuggestions
          .map(
            (item) => item.suggestionId == suggestion.suggestionId
                ? item.copyWith(status: SuggestionStatus.rejected)
                : item,
          )
          .toList(),
    );
  }
}

NoteDraft _applyValue(NoteDraft draft, EditableField field, Object value) {
  switch (field) {
    case EditableField.title:
      return draft.copyWith(titleCandidates: _asStringList(value));
    case EditableField.body:
      return draft.copyWith(body: value.toString());
    case EditableField.hashtags:
      return draft.copyWith(hashtags: _asStringList(value));
    case EditableField.coverCopy:
      return draft.copyWith(coverCopy: value.toString());
  }
}

List<String> _asStringList(Object value) {
  if (value is List<dynamic>) return value.cast<String>();
  return [value.toString()];
}

bool _sameValue(Object left, Object right) {
  if (left is List<dynamic> && right is List<dynamic>) {
    if (left.length != right.length) return false;
    for (var index = 0; index < left.length; index++) {
      if (left[index] != right[index]) return false;
    }
    return true;
  }
  return left == right;
}
