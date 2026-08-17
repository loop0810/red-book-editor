import 'dart:typed_data';

enum NoteStatus { draft, needsReview, ready, published, discarded }

enum RiskLevel { none, warning, blocking }

enum ClaimSupport { supported, uncertain, unsupported }

enum StyleForm { popularScience, experience, advertorial }

enum EditableField { title, body, hashtags, coverCopy }

enum SuggestionStatus { pending, accepted, rejected, stale }

SuggestionStatus suggestionStatusFromApi(String value) {
  switch (value) {
    case 'accepted':
      return SuggestionStatus.accepted;
    case 'rejected':
      return SuggestionStatus.rejected;
    case 'stale':
      return SuggestionStatus.stale;
    default:
      return SuggestionStatus.pending;
  }
}

String suggestionStatusToApi(SuggestionStatus status) {
  switch (status) {
    case SuggestionStatus.pending:
      return 'pending';
    case SuggestionStatus.accepted:
      return 'accepted';
    case SuggestionStatus.rejected:
      return 'rejected';
    case SuggestionStatus.stale:
      return 'stale';
  }
}

String editableFieldToApi(EditableField field) {
  switch (field) {
    case EditableField.title:
      return 'title';
    case EditableField.body:
      return 'body';
    case EditableField.hashtags:
      return 'hashtags';
    case EditableField.coverCopy:
      return 'cover_copy';
  }
}

EditableField editableFieldFromApi(String value) {
  switch (value) {
    case 'body':
      return EditableField.body;
    case 'hashtags':
      return EditableField.hashtags;
    case 'cover_copy':
      return EditableField.coverCopy;
    default:
      return EditableField.title;
  }
}

String styleFormToApi(StyleForm form) {
  // Dart enum 使用 camelCase，HTTP 契约使用 snake_case；转换集中放在这里。
  switch (form) {
    case StyleForm.popularScience:
      return 'popular_science';
    case StyleForm.experience:
      return 'experience';
    case StyleForm.advertorial:
      return 'advertorial';
  }
}

StyleForm styleFormFromApi(String value) {
  // 对未知表达形式回退到 experience，避免服务端增加新值后客户端直接崩溃。
  switch (value) {
    case 'popular_science':
      return StyleForm.popularScience;
    case 'advertorial':
      return StyleForm.advertorial;
    default:
      return StyleForm.experience;
  }
}

String styleFormDisplayName(StyleForm form) {
  switch (form) {
    case StyleForm.popularScience:
      return '科普';
    case StyleForm.experience:
      return '经验';
    case StyleForm.advertorial:
      return '软文';
  }
}

class SourceExperience {
  // 这是跨端最重要的事实输入对象：用户写什么，Agent 就应该以它为事实边界。
  const SourceExperience({
    required this.babyMonth,
    required this.scenario,
    required this.actions,
    this.observations = '',
    this.notes = '',
    this.assetIds = const [],
  });

  final int babyMonth;
  final String scenario;
  final List<String> actions;
  final String observations;
  final String notes;
  final List<String> assetIds;

  Map<String, Object> toJson() => {
    // 字段名必须和 docs/contracts 及 Python SourceExperienceDto 保持一致。
    'baby_month': babyMonth,
    'scenario': scenario,
    'actions': actions,
    'observations': observations,
    'notes': notes,
    'asset_ids': assetIds,
  };

  factory SourceExperience.fromJson(Map<String, dynamic> json) {
    // API 返回 JSON 后，在这里恢复为页面使用的 Dart model。
    return SourceExperience(
      babyMonth: json['baby_month'] as int,
      scenario: json['scenario'] as String,
      actions: (json['actions'] as List<dynamic>? ?? const []).cast<String>(),
      observations: json['observations'] as String? ?? '',
      notes: json['notes'] as String? ?? '',
      assetIds: (json['asset_ids'] as List<dynamic>? ?? const [])
          .cast<String>(),
    );
  }
}

class ContentBrief {
  const ContentBrief({
    required this.focus,
    required this.rawMaterial,
    this.domainContext = const {},
    this.assetIds = const [],
  });

  final String focus;
  final String rawMaterial;
  final Map<String, Object?> domainContext;
  final List<String> assetIds;

  Map<String, Object?> toJson() => {
    'focus': focus,
    'raw_material': rawMaterial,
    'domain_context': domainContext,
    'asset_ids': assetIds,
  };

  factory ContentBrief.fromJson(Map<String, dynamic> json) => ContentBrief(
    focus: json['focus'] as String? ?? '',
    rawMaterial: json['raw_material'] as String? ?? '',
    domainContext:
        (json['domain_context'] as Map<dynamic, dynamic>? ?? const {}).map(
          (key, value) => MapEntry(key.toString(), value),
        ),
    assetIds: (json['asset_ids'] as List<dynamic>? ?? const []).cast<String>(),
  );

  factory ContentBrief.fromLegacy(SourceExperience source) => ContentBrief(
    focus: source.scenario,
    rawMaterial: [
      if (source.actions.isNotEmpty) source.actions.join('；'),
      if (source.observations.isNotEmpty) source.observations,
      if (source.notes.isNotEmpty) source.notes,
    ].join('\n'),
    domainContext: {'baby_month': source.babyMonth},
    assetIds: source.assetIds,
  );
}

class UserFacingIssue {
  const UserFacingIssue({
    required this.category,
    required this.message,
    this.field,
    this.action,
  });

  final String category;
  final String message;
  final String? field;
  final String? action;

  factory UserFacingIssue.fromJson(Map<String, dynamic> json) =>
      UserFacingIssue(
        category: json['category'] as String? ?? 'review',
        message: json['message'] as String? ?? '',
        field: json['field'] as String?,
        action: json['action'] as String?,
      );
}

class AccountProfile {
  const AccountProfile({
    required this.accountId,
    required this.domainId,
    required this.positioning,
    required this.tone,
    this.domainContext = const {},
    this.currentBabyMonth,
    this.boundaries = const [],
    this.commonExpressions = const [],
  });

  final String accountId;
  final String domainId;
  final String positioning;
  final String tone;
  final Map<String, Object?> domainContext;
  final int? currentBabyMonth;
  final List<String> boundaries;
  final List<String> commonExpressions;

  factory AccountProfile.fromJson(Map<String, dynamic> json) => AccountProfile(
    accountId: json['account_id'] as String,
    domainId: json['domain_id'] as String? ?? 'parenting',
    positioning: json['positioning'] as String? ?? '',
    tone: json['tone'] as String? ?? '',
    domainContext:
        (json['domain_context'] as Map<dynamic, dynamic>? ?? const {}).map(
          (key, value) => MapEntry(key.toString(), value),
        ),
    currentBabyMonth: json['current_baby_month'] as int?,
    boundaries: (json['boundaries'] as List<dynamic>? ?? const [])
        .cast<String>(),
    commonExpressions:
        (json['common_expressions'] as List<dynamic>? ?? const [])
            .cast<String>(),
  );

  Map<String, Object?> toJson() => {
    'domain_id': domainId,
    'domain_context': domainContext,
    'positioning': positioning,
    'tone': tone,
    'current_baby_month': currentBabyMonth,
    'boundaries': boundaries,
    'common_expressions': commonExpressions,
  };
}

class ContentColumn {
  const ContentColumn({
    required this.columnId,
    required this.accountId,
    required this.name,
    required this.description,
    this.contentTypes = const [],
    this.enabled = true,
  });

  final String columnId;
  final String accountId;
  final String name;
  final String description;
  final List<String> contentTypes;
  final bool enabled;

  factory ContentColumn.fromJson(Map<String, dynamic> json) => ContentColumn(
    columnId: json['column_id'] as String,
    accountId: json['account_id'] as String,
    name: json['name'] as String? ?? '',
    description: json['description'] as String? ?? '',
    contentTypes: (json['content_types'] as List<dynamic>? ?? const [])
        .cast<String>(),
    enabled: json['enabled'] as bool? ?? true,
  );
}

class ReviewFinding {
  const ReviewFinding({
    required this.level,
    required this.code,
    required this.message,
    this.field,
    this.matchedText,
    this.evidenceFactIds = const [],
  });

  final RiskLevel level;
  final String code;
  final String message;
  final String? field;
  final String? matchedText;
  final List<String> evidenceFactIds;
}

class FieldSuggestion {
  const FieldSuggestion({
    required this.suggestionId,
    required this.noteId,
    required this.field,
    required this.value,
    required this.baseFieldDigest,
    required this.baseContentDigest,
    this.review,
    this.evidence = const [],
    this.evidenceFactIds = const [],
    this.createdAt = '',
    this.status = SuggestionStatus.pending,
    this.baseValue,
  });

  final String suggestionId;
  final String noteId;
  final EditableField field;
  final Object value;
  final String baseFieldDigest;
  final String baseContentDigest;
  final ReviewResult? review;
  final List<String> evidence;
  final List<String> evidenceFactIds;
  final String createdAt;
  final SuggestionStatus status;
  final Object? baseValue;

  List<String> get listValue => value is List<dynamic>
      ? (value as List<dynamic>).cast<String>()
      : const [];

  String get textValue =>
      value is String ? value as String : listValue.join(' ');

  FieldSuggestion copyWith({SuggestionStatus? status, Object? baseValue}) {
    return FieldSuggestion(
      suggestionId: suggestionId,
      noteId: noteId,
      field: field,
      value: value,
      baseFieldDigest: baseFieldDigest,
      baseContentDigest: baseContentDigest,
      review: review,
      evidence: evidence,
      evidenceFactIds: evidenceFactIds,
      createdAt: createdAt,
      status: status ?? this.status,
      baseValue: baseValue ?? this.baseValue,
    );
  }

  factory FieldSuggestion.fromJson(Map<String, dynamic> json) {
    final rawValue = json['value'];
    final value = rawValue is List<dynamic>
        ? rawValue.cast<String>()
        : rawValue as String? ?? '';
    return FieldSuggestion(
      suggestionId: json['suggestion_id'] as String,
      noteId: json['note_id'] as String,
      field: editableFieldFromApi(json['field'] as String? ?? 'title'),
      value: value,
      baseFieldDigest: json['base_field_digest'] as String? ?? '',
      baseContentDigest: json['base_content_digest'] as String? ?? '',
      review: json['review'] is Map<String, dynamic>
          ? ReviewResult.fromJson(json['review'] as Map<String, dynamic>)
          : null,
      evidence: (json['evidence'] as List<dynamic>? ?? const []).cast<String>(),
      evidenceFactIds: (json['evidence_fact_ids'] as List<dynamic>? ?? const [])
          .cast<String>(),
      status: suggestionStatusFromApi(json['status'] as String? ?? 'pending'),
      createdAt: json['created_at'] as String? ?? '',
    );
  }

  Map<String, Object?> toJson() => {
    'suggestion_id': suggestionId,
    'note_id': noteId,
    'field': editableFieldToApi(field),
    'value': value,
    'base_field_digest': baseFieldDigest,
    'base_content_digest': baseContentDigest,
    'review': review?.toJson(),
    'evidence': evidence,
    'evidence_fact_ids': evidenceFactIds,
    'status': suggestionStatusToApi(status),
    'created_at': createdAt,
  };
}

class ClaimAuditItem {
  const ClaimAuditItem({
    required this.field,
    required this.claim,
    required this.support,
    this.evidenceFactIds = const [],
    this.evidence = const [],
    this.reason = '',
    this.level = RiskLevel.none,
  });

  final String field;
  final String claim;
  final ClaimSupport support;
  final List<String> evidenceFactIds;
  final List<String> evidence;
  final String reason;
  final RiskLevel level;
}

class ReviewResult {
  const ReviewResult({
    required this.passed,
    this.findings = const [],
    this.claimAudit = const [],
    this.sourceDigest,
    this.contentDigest,
    this.auditVersion,
    this.policyVersion,
  });

  final bool passed;
  final List<ReviewFinding> findings;
  final List<ClaimAuditItem> claimAudit;
  final String? sourceDigest;
  final String? contentDigest;
  final String? auditVersion;
  final String? policyVersion;

  factory ReviewResult.fromJson(Map<String, dynamic> json) {
    return ReviewResult(
      passed: json['passed'] as bool? ?? false,
      findings: _reviewFindingsFromJson(json['findings']),
      claimAudit: _claimAuditFromJson(json['claim_audit']),
      sourceDigest: json['source_digest'] as String?,
      contentDigest: json['content_digest'] as String?,
      auditVersion: json['audit_version'] as String?,
      policyVersion: json['policy_version'] as String?,
    );
  }

  Map<String, Object?> toJson() => {
    'passed': passed,
    'findings': findings
        .map(
          (finding) => {
            'level': _riskLevelToApi(finding.level),
            'code': finding.code,
            'message': finding.message,
            'field': finding.field,
            'matched_text': finding.matchedText,
            'evidence_fact_ids': finding.evidenceFactIds,
          },
        )
        .toList(),
    'claim_audit': claimAudit
        .map(
          (item) => {
            'field': item.field,
            'claim': item.claim,
            'support': _claimSupportToApi(item.support),
            'evidence_fact_ids': item.evidenceFactIds,
            'evidence': item.evidence,
            'reason': item.reason,
            'level': _riskLevelToApi(item.level),
          },
        )
        .toList(),
    'source_digest': sourceDigest,
    'content_digest': contentDigest,
    'audit_version': auditVersion,
    'policy_version': policyVersion,
  };
}

class NoteDraft {
  // NoteDraft 同时包含来源事实、生成字段、审核结果和版本时间，是编辑器的核心状态。
  const NoteDraft({
    required this.noteId,
    required this.accountId,
    required this.columnId,
    required this.status,
    this.source,
    this.contentBrief,
    this.domainId = 'parenting',
    this.topicAngle = '',
    this.titleCandidates = const [],
    this.body = '',
    this.hashtags = const [],
    this.coverCopy = '',
    this.imageSuggestions = const [],
    this.styleForm,
    this.review,
    this.userIssue,
    this.updatedAt = '',
  });

  final String noteId;
  final String accountId;
  final String columnId;
  final NoteStatus status;
  final SourceExperience? source;
  final ContentBrief? contentBrief;
  final String domainId;
  final String topicAngle;
  final List<String> titleCandidates;
  final String body;
  final List<String> hashtags;
  final String coverCopy;
  final List<String> imageSuggestions;
  final StyleForm? styleForm;
  final ReviewResult? review;
  final UserFacingIssue? userIssue;
  final String updatedAt;

  List<ReviewFinding> get reviewFindings => review?.findings ?? const [];
  String get focus => contentBrief?.focus ?? source?.scenario ?? '';

  factory NoteDraft.fromJson(Map<String, dynamic> json) {
    // fromJson 负责把服务端完整响应拆成类型安全对象；缺省字段提供向后兼容。
    return NoteDraft(
      noteId: json['note_id'] as String,
      accountId: json['account_id'] as String,
      columnId: json['column_id'] as String,
      status: _noteStatusFromApi(json['status'] as String),
      source: json['source'] is Map<String, dynamic>
          ? SourceExperience.fromJson(json['source'] as Map<String, dynamic>)
          : null,
      contentBrief: json['content_brief'] is Map<String, dynamic>
          ? ContentBrief.fromJson(json['content_brief'] as Map<String, dynamic>)
          : (json['source'] is Map<String, dynamic>
                ? ContentBrief.fromLegacy(
                    SourceExperience.fromJson(
                      json['source'] as Map<String, dynamic>,
                    ),
                  )
                : null),
      domainId: json['domain_id'] as String? ?? 'parenting',
      topicAngle: json['topic_angle'] as String? ?? '',
      titleCandidates: (json['title_candidates'] as List<dynamic>? ?? const [])
          .cast<String>(),
      body: json['body'] as String? ?? '',
      hashtags: (json['hashtags'] as List<dynamic>? ?? const []).cast<String>(),
      coverCopy: json['cover_copy'] as String? ?? '',
      imageSuggestions:
          (json['image_suggestions'] as List<dynamic>? ?? const [])
              .cast<String>(),
      styleForm: json['style_form'] is String
          ? styleFormFromApi(json['style_form'] as String)
          : null,
      review: json['review'] is Map<String, dynamic>
          ? ReviewResult.fromJson(json['review'] as Map<String, dynamic>)
          : null,
      userIssue: json['user_issue'] is Map<String, dynamic>
          ? UserFacingIssue.fromJson(json['user_issue'] as Map<String, dynamic>)
          : null,
      updatedAt: json['updated_at'] as String? ?? '',
    );
  }

  Map<String, Object?> toJson() => {
    // 保存或重生成时，编辑器把当前 draft 再编码回 API 契约。
    'note_id': noteId,
    'account_id': accountId,
    'column_id': columnId,
    'status': _noteStatusToApi(status),
    'domain_id': domainId,
    'topic_angle': topicAngle,
    'title_candidates': titleCandidates,
    'body': body,
    'hashtags': hashtags,
    'cover_copy': coverCopy,
    'image_suggestions': imageSuggestions,
    'style_form': styleForm == null ? null : styleFormToApi(styleForm!),
    if (source != null) 'source': source!.toJson(),
    if (contentBrief != null) 'content_brief': contentBrief!.toJson(),
    'review': review?.toJson(),
    'user_issue': userIssue == null
        ? null
        : {
            'category': userIssue!.category,
            'message': userIssue!.message,
            'field': userIssue!.field,
            'action': userIssue!.action,
          },
    'updated_at': updatedAt,
  };

  NoteDraft copyWith({
    NoteStatus? status,
    String? topicAngle,
    List<String>? titleCandidates,
    String? body,
    List<String>? hashtags,
    String? coverCopy,
    List<String>? imageSuggestions,
    StyleForm? styleForm,
    ReviewResult? review,
    ContentBrief? contentBrief,
    String? domainId,
    UserFacingIssue? userIssue,
    String? updatedAt,
  }) {
    // copyWith 用于局部修改：只替换用户刚编辑的字段，其他字段沿用原对象。
    return NoteDraft(
      noteId: noteId,
      accountId: accountId,
      columnId: columnId,
      status: status ?? this.status,
      source: source,
      contentBrief: contentBrief ?? this.contentBrief,
      domainId: domainId ?? this.domainId,
      topicAngle: topicAngle ?? this.topicAngle,
      titleCandidates: titleCandidates ?? this.titleCandidates,
      body: body ?? this.body,
      hashtags: hashtags ?? this.hashtags,
      coverCopy: coverCopy ?? this.coverCopy,
      imageSuggestions: imageSuggestions ?? this.imageSuggestions,
      styleForm: styleForm ?? this.styleForm,
      review: review ?? this.review,
      userIssue: userIssue ?? this.userIssue,
      updatedAt: updatedAt ?? this.updatedAt,
    );
  }
}

class AgentTraceStep {
  // trace 是可展示的执行摘要，不是模型的完整思维过程，也不参与生成结果计算。
  const AgentTraceStep({
    required this.order,
    required this.kind,
    required this.label,
    required this.summary,
    this.phase,
  });

  final int order;
  final String kind;
  final String label;
  final String summary;
  final String? phase;

  factory AgentTraceStep.fromJson(Map<String, dynamic> json) {
    // 服务端按 order 返回步骤，编辑器据此展示“读取档案/自评/定稿”等阶段。
    return AgentTraceStep(
      order: json['order'] as int,
      kind: json['kind'] as String? ?? 'phase',
      label: json['label'] as String? ?? '',
      summary: json['summary'] as String? ?? '',
      phase: json['phase'] as String?,
    );
  }
}

class AgentRunDiagnostics {
  const AgentRunDiagnostics({
    required this.status,
    required this.phase,
    this.steps = 0,
    this.revisions = 0,
    this.toolCalls = 0,
    this.repeatedErrors = 0,
    this.failureCode,
  });

  final String status;
  final String? phase;
  final int steps;
  final int revisions;
  final int toolCalls;
  final int repeatedErrors;
  final String? failureCode;

  factory AgentRunDiagnostics.fromJson(Map<String, dynamic> json) {
    return AgentRunDiagnostics(
      status: json['status'] as String? ?? 'failed',
      phase: json['phase'] as String?,
      steps: json['steps'] as int? ?? 0,
      revisions: json['revisions'] as int? ?? 0,
      toolCalls: json['tool_calls'] as int? ?? 0,
      repeatedErrors: json['repeated_errors'] as int? ?? 0,
      failureCode: json['failure_code'] as String?,
    );
  }
}

class AgentRun {
  const AgentRun({
    required this.runId,
    required this.noteId,
    required this.accountId,
    required this.columnId,
    required this.operation,
    required this.form,
    required this.status,
    required this.attempt,
    required this.cancelRequested,
    required this.createdAt,
    required this.updatedAt,
    this.currentPhase,
    this.diagnostics,
    this.failureCode,
    this.startedAt,
    this.finishedAt,
  });

  final String runId;
  final String noteId;
  final String accountId;
  final String columnId;
  final String operation;
  final StyleForm form;
  final String status;
  final String? currentPhase;
  final int attempt;
  final bool cancelRequested;
  final AgentRunDiagnostics? diagnostics;
  final String? failureCode;
  final String createdAt;
  final String updatedAt;
  final String? startedAt;
  final String? finishedAt;

  factory AgentRun.fromJson(Map<String, dynamic> json) {
    return AgentRun(
      runId: json['run_id'] as String,
      noteId: json['note_id'] as String,
      accountId: json['account_id'] as String,
      columnId: json['column_id'] as String,
      operation: json['operation'] as String? ?? 'generate',
      form: styleFormFromApi(json['form'] as String? ?? 'experience'),
      status: json['status'] as String? ?? 'failed',
      currentPhase: json['current_phase'] as String?,
      attempt: json['attempt'] as int? ?? 1,
      cancelRequested: json['cancel_requested'] as bool? ?? false,
      diagnostics: json['diagnostics'] is Map<String, dynamic>
          ? AgentRunDiagnostics.fromJson(
              json['diagnostics'] as Map<String, dynamic>,
            )
          : null,
      failureCode: json['failure_code'] as String?,
      createdAt: json['created_at'] as String? ?? '',
      updatedAt: json['updated_at'] as String? ?? '',
      startedAt: json['started_at'] as String?,
      finishedAt: json['finished_at'] as String?,
    );
  }
}

class AgentRunEvent {
  const AgentRunEvent({
    required this.runId,
    required this.sequence,
    required this.eventType,
    required this.label,
    required this.summary,
    required this.attempt,
    this.phase,
    this.status,
    this.failureCode,
    this.createdAt,
  });

  final String runId;
  final int sequence;
  final String eventType;
  final String? phase;
  final String label;
  final String summary;
  final String? status;
  final String? failureCode;
  final int attempt;
  final String? createdAt;

  factory AgentRunEvent.fromJson(Map<String, dynamic> json) {
    return AgentRunEvent(
      runId: json['run_id'] as String,
      sequence: json['sequence'] as int,
      eventType: json['event_type'] as String? ?? 'phase',
      phase: json['phase'] as String?,
      label: json['label'] as String? ?? '',
      summary: json['summary'] as String? ?? '',
      status: json['status'] as String?,
      failureCode: json['failure_code'] as String?,
      attempt: json['attempt'] as int? ?? 1,
      createdAt: json['created_at'] as String?,
    );
  }
}

class StyledNoteResponse {
  // 生成接口的组合响应：draft 给编辑器，agentTrace 给调试/学习面板。
  const StyledNoteResponse({
    required this.draft,
    this.agentTrace = const [],
    this.userResult,
  });

  final NoteDraft draft;
  final List<AgentTraceStep> agentTrace;
  final UserResultProjection? userResult;

  factory StyledNoteResponse.fromJson(Map<String, dynamic> json) {
    final resultJson = json['user_result'] as Map<String, dynamic>?;
    final publicDraftJson = json['draft'] as Map<String, dynamic>?;
    final draftJson = _draftJsonFromProjection(
      publicDraftJson ?? resultJson ?? <String, dynamic>{},
    );
    final issues = json['issues'] as List<dynamic>? ?? const [];
    if (draftJson['user_issue'] == null && issues.isNotEmpty) {
      draftJson['user_issue'] = issues.first;
    }
    return StyledNoteResponse(
      draft: NoteDraft.fromJson(draftJson),
      agentTrace: (json['agent_trace'] as List<dynamic>? ?? const [])
          .whereType<Map<String, dynamic>>()
          .map(AgentTraceStep.fromJson)
          .toList(),
      userResult: json['user_result'] is Map<String, dynamic>
          ? UserResultProjection.fromJson(
              json['user_result'] as Map<String, dynamic>,
            )
          : null,
    );
  }
}

Map<String, dynamic> _draftJsonFromProjection(Map<String, dynamic> json) {
  final draft = <String, dynamic>{...json};
  if (draft['content_brief'] is! Map<String, dynamic> &&
      draft['source'] is! Map<String, dynamic>) {
    draft['content_brief'] = {
      'focus': draft['focus'] as String? ?? '',
      'raw_material': draft['body'] as String? ?? '',
    };
  }
  if (draft['user_issue'] == null && draft['issue'] != null) {
    draft['user_issue'] = draft['issue'];
  }
  return draft;
}

class UserResultProjection {
  const UserResultProjection({
    required this.noteId,
    required this.focus,
    required this.titleCandidates,
    required this.body,
    required this.hashtags,
    required this.imageSuggestions,
    this.coverCopy = '',
    this.contentBrief,
    this.issue,
  });

  final String noteId;
  final String focus;
  final List<String> titleCandidates;
  final String body;
  final List<String> hashtags;
  final String coverCopy;
  final List<String> imageSuggestions;
  final ContentBrief? contentBrief;
  final UserFacingIssue? issue;

  factory UserResultProjection.fromJson(
    Map<String, dynamic> json,
  ) => UserResultProjection(
    noteId: json['note_id'] as String? ?? '',
    focus: json['focus'] as String? ?? '',
    titleCandidates: (json['title_candidates'] as List<dynamic>? ?? const [])
        .cast<String>(),
    body: json['body'] as String? ?? '',
    hashtags: (json['hashtags'] as List<dynamic>? ?? const []).cast<String>(),
    coverCopy: json['cover_copy'] as String? ?? '',
    imageSuggestions: (json['image_suggestions'] as List<dynamic>? ?? const [])
        .cast<String>(),
    contentBrief: json['content_brief'] is Map<String, dynamic>
        ? ContentBrief.fromJson(json['content_brief'] as Map<String, dynamic>)
        : null,
    issue: json['issue'] is Map<String, dynamic>
        ? UserFacingIssue.fromJson(json['issue'] as Map<String, dynamic>)
        : null,
  );
}

class Asset {
  const Asset({
    required this.assetId,
    required this.accountId,
    required this.filename,
    required this.contentType,
    this.position = 0,
  });

  final String assetId;
  final String accountId;
  final String filename;
  final String contentType;
  final int position;

  factory Asset.fromJson(Map<String, dynamic> json) {
    return Asset(
      assetId: json['asset_id'] as String,
      accountId: json['account_id'] as String,
      filename: json['filename'] as String,
      contentType: json['content_type'] as String,
      position: json['position'] as int? ?? 0,
    );
  }
}

class NoteDraftVersion {
  const NoteDraftVersion({
    required this.version,
    this.topicAngle = '',
    this.titleCandidates = const [],
    this.body = '',
    this.hashtags = const [],
    this.coverCopy = '',
    this.imageSuggestions = const [],
    this.styleForm,
    this.review,
    this.createdAt = '',
  });

  final int version;
  final String topicAngle;
  final List<String> titleCandidates;
  final String body;
  final List<String> hashtags;
  final String coverCopy;
  final List<String> imageSuggestions;
  final StyleForm? styleForm;
  final ReviewResult? review;
  final String createdAt;

  factory NoteDraftVersion.fromJson(Map<String, dynamic> json) {
    return NoteDraftVersion(
      version: json['version'] as int,
      topicAngle: json['topic_angle'] as String? ?? '',
      titleCandidates: (json['title_candidates'] as List<dynamic>? ?? const [])
          .cast<String>(),
      body: json['body'] as String? ?? '',
      hashtags: (json['hashtags'] as List<dynamic>? ?? const []).cast<String>(),
      coverCopy: json['cover_copy'] as String? ?? '',
      imageSuggestions:
          (json['image_suggestions'] as List<dynamic>? ?? const [])
              .cast<String>(),
      styleForm: json['style_form'] is String
          ? styleFormFromApi(json['style_form'] as String)
          : null,
      review: json['review'] is Map<String, dynamic>
          ? ReviewResult.fromJson(json['review'] as Map<String, dynamic>)
          : null,
      createdAt: json['created_at'] as String? ?? '',
    );
  }
}

class DownloadedAsset {
  const DownloadedAsset({
    required this.bytes,
    required this.filename,
    required this.contentType,
  });

  final Uint8List bytes;
  final String filename;
  final String contentType;
}

List<ReviewFinding> _reviewFindingsFromJson(Object? value) {
  final findings = value;
  if (findings is! List<dynamic>) return const [];
  return findings.whereType<Map<String, dynamic>>().map((finding) {
    final level = switch (finding['level']) {
      'blocking' => RiskLevel.blocking,
      'warning' => RiskLevel.warning,
      _ => RiskLevel.none,
    };
    return ReviewFinding(
      level: level,
      code: finding['code'] as String? ?? 'unknown',
      message: finding['message'] as String? ?? '',
      field: finding['field'] as String?,
      matchedText: finding['matched_text'] as String?,
      evidenceFactIds:
          (finding['evidence_fact_ids'] as List<dynamic>? ?? const [])
              .cast<String>(),
    );
  }).toList();
}

List<ClaimAuditItem> _claimAuditFromJson(Object? value) {
  if (value is! List<dynamic>) return const [];
  return value.whereType<Map<String, dynamic>>().map((item) {
    final support = switch (item['support']) {
      'supported' => ClaimSupport.supported,
      'uncertain' => ClaimSupport.uncertain,
      _ => ClaimSupport.unsupported,
    };
    final level = switch (item['level']) {
      'blocking' => RiskLevel.blocking,
      'warning' => RiskLevel.warning,
      _ => RiskLevel.none,
    };
    return ClaimAuditItem(
      field: item['field'] as String? ?? '',
      claim: item['claim'] as String? ?? '',
      support: support,
      evidenceFactIds: (item['evidence_fact_ids'] as List<dynamic>? ?? const [])
          .cast<String>(),
      evidence: (item['evidence'] as List<dynamic>? ?? const []).cast<String>(),
      reason: item['reason'] as String? ?? '',
      level: level,
    );
  }).toList();
}

NoteStatus _noteStatusFromApi(String value) {
  // 状态值是跨端契约的一部分，未知值安全回退为 draft。
  switch (value) {
    case 'needs_review':
      return NoteStatus.needsReview;
    case 'ready':
      return NoteStatus.ready;
    case 'published':
      return NoteStatus.published;
    case 'discarded':
      return NoteStatus.discarded;
    default:
      return NoteStatus.draft;
  }
}

String _noteStatusToApi(NoteStatus status) {
  // 保存草稿时把 Dart enum 转回 API 使用的字符串。
  switch (status) {
    case NoteStatus.needsReview:
      return 'needs_review';
    case NoteStatus.ready:
      return 'ready';
    case NoteStatus.published:
      return 'published';
    case NoteStatus.discarded:
      return 'discarded';
    case NoteStatus.draft:
      return 'draft';
  }
}

String _riskLevelToApi(RiskLevel level) {
  // 审核风险等级同样需要在 Dart enum 和 JSON 字符串之间双向转换。
  switch (level) {
    case RiskLevel.blocking:
      return 'blocking';
    case RiskLevel.warning:
      return 'warning';
    case RiskLevel.none:
      return 'none';
  }
}

String _claimSupportToApi(ClaimSupport support) {
  switch (support) {
    case ClaimSupport.supported:
      return 'supported';
    case ClaimSupport.uncertain:
      return 'uncertain';
    case ClaimSupport.unsupported:
      return 'unsupported';
  }
}
