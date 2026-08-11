import 'dart:typed_data';

enum NoteStatus { draft, needsReview, ready, published, discarded }

enum RiskLevel { none, warning, blocking }

enum StyleForm { popularScience, experience, advertorial }

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

class ReviewFinding {
  const ReviewFinding({
    required this.level,
    required this.code,
    required this.message,
    this.matchedText,
  });

  final RiskLevel level;
  final String code;
  final String message;
  final String? matchedText;
}

class NoteDraft {
  // NoteDraft 同时包含来源事实、生成字段、审核结果和版本时间，是编辑器的核心状态。
  const NoteDraft({
    required this.noteId,
    required this.accountId,
    required this.columnId,
    required this.status,
    required this.source,
    this.topicAngle = '',
    this.titleCandidates = const [],
    this.body = '',
    this.hashtags = const [],
    this.coverCopy = '',
    this.imageSuggestions = const [],
    this.reviewFindings = const [],
    this.updatedAt = '',
  });

  final String noteId;
  final String accountId;
  final String columnId;
  final NoteStatus status;
  final SourceExperience source;
  final String topicAngle;
  final List<String> titleCandidates;
  final String body;
  final List<String> hashtags;
  final String coverCopy;
  final List<String> imageSuggestions;
  final List<ReviewFinding> reviewFindings;
  final String updatedAt;

  factory NoteDraft.fromJson(Map<String, dynamic> json) {
    // fromJson 负责把服务端完整响应拆成类型安全对象；缺省字段提供向后兼容。
    return NoteDraft(
      noteId: json['note_id'] as String,
      accountId: json['account_id'] as String,
      columnId: json['column_id'] as String,
      status: _noteStatusFromApi(json['status'] as String),
      source: SourceExperience.fromJson(json['source'] as Map<String, dynamic>),
      topicAngle: json['topic_angle'] as String? ?? '',
      titleCandidates: (json['title_candidates'] as List<dynamic>? ?? const [])
          .cast<String>(),
      body: json['body'] as String? ?? '',
      hashtags: (json['hashtags'] as List<dynamic>? ?? const []).cast<String>(),
      coverCopy: json['cover_copy'] as String? ?? '',
      imageSuggestions:
          (json['image_suggestions'] as List<dynamic>? ?? const [])
              .cast<String>(),
      reviewFindings: _reviewFindingsFromJson(json['review']),
      updatedAt: json['updated_at'] as String? ?? '',
    );
  }

  Map<String, Object?> toJson() => {
    // 保存或重生成时，编辑器把当前 draft 再编码回 API 契约。
    'note_id': noteId,
    'account_id': accountId,
    'column_id': columnId,
    'status': _noteStatusToApi(status),
    'topic_angle': topicAngle,
    'title_candidates': titleCandidates,
    'body': body,
    'hashtags': hashtags,
    'cover_copy': coverCopy,
    'image_suggestions': imageSuggestions,
    'source': source.toJson(),
    'review': reviewFindings.isEmpty
        ? null
        : {
            'passed': !reviewFindings.any(
              (finding) => finding.level == RiskLevel.blocking,
            ),
            'findings': reviewFindings
                .map(
                  (finding) => {
                    'level': _riskLevelToApi(finding.level),
                    'code': finding.code,
                    'message': finding.message,
                    'matched_text': finding.matchedText,
                  },
                )
                .toList(),
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
    List<ReviewFinding>? reviewFindings,
    String? updatedAt,
  }) {
    // copyWith 用于局部修改：只替换用户刚编辑的字段，其他字段沿用原对象。
    return NoteDraft(
      noteId: noteId,
      accountId: accountId,
      columnId: columnId,
      status: status ?? this.status,
      source: source,
      topicAngle: topicAngle ?? this.topicAngle,
      titleCandidates: titleCandidates ?? this.titleCandidates,
      body: body ?? this.body,
      hashtags: hashtags ?? this.hashtags,
      coverCopy: coverCopy ?? this.coverCopy,
      imageSuggestions: imageSuggestions ?? this.imageSuggestions,
      reviewFindings: reviewFindings ?? this.reviewFindings,
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
  });

  final int order;
  final String kind;
  final String label;
  final String summary;

  factory AgentTraceStep.fromJson(Map<String, dynamic> json) {
    // 服务端按 order 返回步骤，编辑器据此展示“读取档案/自评/定稿”等阶段。
    return AgentTraceStep(
      order: json['order'] as int,
      kind: json['kind'] as String? ?? 'phase',
      label: json['label'] as String? ?? '',
      summary: json['summary'] as String? ?? '',
    );
  }
}

class StyledNoteResponse {
  // 生成接口的组合响应：draft 给编辑器，agentTrace 给调试/学习面板。
  const StyledNoteResponse({required this.draft, required this.agentTrace});

  final NoteDraft draft;
  final List<AgentTraceStep> agentTrace;

  factory StyledNoteResponse.fromJson(Map<String, dynamic> json) {
    return StyledNoteResponse(
      draft: NoteDraft.fromJson(json['draft'] as Map<String, dynamic>),
      agentTrace: (json['agent_trace'] as List<dynamic>? ?? const [])
          .whereType<Map<String, dynamic>>()
          .map(AgentTraceStep.fromJson)
          .toList(),
    );
  }
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
    this.createdAt = '',
  });

  final int version;
  final String topicAngle;
  final List<String> titleCandidates;
  final String body;
  final List<String> hashtags;
  final String coverCopy;
  final List<String> imageSuggestions;
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
  // review 可能为空；客户端把它统一转换成列表，页面只需判断风险等级。
  final review = value is Map<String, dynamic> ? value : null;
  final findings = review?['findings'];
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
      matchedText: finding['matched_text'] as String?,
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
