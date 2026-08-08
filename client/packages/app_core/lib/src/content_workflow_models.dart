import 'dart:typed_data';

enum NoteStatus { draft, needsReview, ready, published, discarded }

enum RiskLevel { none, warning, blocking }

enum StyleForm { popularScience, experience, advertorial }

String styleFormToApi(StyleForm form) {
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
    'baby_month': babyMonth,
    'scenario': scenario,
    'actions': actions,
    'observations': observations,
    'notes': notes,
    'asset_ids': assetIds,
  };

  factory SourceExperience.fromJson(Map<String, dynamic> json) {
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
    return AgentTraceStep(
      order: json['order'] as int,
      kind: json['kind'] as String? ?? 'phase',
      label: json['label'] as String? ?? '',
      summary: json['summary'] as String? ?? '',
    );
  }
}

class StyledNoteResponse {
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
  switch (level) {
    case RiskLevel.blocking:
      return 'blocking';
    case RiskLevel.warning:
      return 'warning';
    case RiskLevel.none:
      return 'none';
  }
}
