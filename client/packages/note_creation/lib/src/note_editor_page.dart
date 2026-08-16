import 'dart:async';

import 'package:app_core/app_core.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import 'note_creation_types.dart';

class NoteEditorPage extends StatefulWidget {
  // 编辑器接收的是服务端返回的 NoteDraft，而保存、重生成、版本读取等能力
  // 都通过回调注入，因此页面可以独立运行在本地模式或真实 API 模式。
  const NoteEditorPage({
    required this.draft,
    this.onPublish,
    this.onRegenerateField,
    this.onSaveDraft,
    this.loadVersions,
    this.loadSuggestions,
    this.onUpdateSuggestionStatus,
    this.agentTrace = const [],
    this.styleForm,
    this.aiBaseline,
    super.key,
  });

  final NoteDraft draft;
  final Future<void> Function()? onPublish;
  final RegenerateField? onRegenerateField;
  final SaveDraft? onSaveDraft;
  final LoadVersions? loadVersions;
  final LoadSuggestions? loadSuggestions;
  final UpdateSuggestionStatus? onUpdateSuggestionStatus;
  final List<AgentTraceStep> agentTrace;
  final StyleForm? styleForm;

  /// A newly generated note has a reliable AI baseline. Reopened drafts may not.
  final NoteDraft? aiBaseline;

  @override
  State<NoteEditorPage> createState() => _NoteEditorPageState();
}

class _LocalVersion {
  const _LocalVersion({
    required this.label,
    required this.title,
    required this.body,
    required this.hashtags,
    required this.coverCopy,
  });

  final String label;
  final String title;
  final String body;
  final String hashtags;
  final String coverCopy;
}

class _NoteEditorPageState extends State<NoteEditorPage> {
  late EditorSessionState _session;
  late final TextEditingController _titleController;
  late final TextEditingController _bodyController;
  late final TextEditingController _hashtagsController;
  late final TextEditingController _coverController;
  final _fieldKeys = <EditableField, GlobalKey>{
    EditableField.title: GlobalKey(),
    EditableField.body: GlobalKey(),
    EditableField.hashtags: GlobalKey(),
    EditableField.coverCopy: GlobalKey(),
  };
  final _fieldFocusNodes = <EditableField, FocusNode>{
    EditableField.title: FocusNode(),
    EditableField.body: FocusNode(),
    EditableField.hashtags: FocusNode(),
    EditableField.coverCopy: FocusNode(),
  };
  final _localVersions = <_LocalVersion>[];
  bool _saving = false;
  String? _regeneratingField;

  NoteDraft get _draft => _session.draft;

  bool get _hasBlockingReview => _draft.reviewFindings.any(
    // blocking 风险只影响“是否允许继续导出/发布”，不等于页面不能继续编辑。
    (finding) => finding.level == RiskLevel.blocking,
  );

  bool get _needsReview => _draft.status == NoteStatus.needsReview;

  @override
  void initState() {
    super.initState();
    // Controller 是输入框的临时 UI 状态，_draft 是跨请求的数据快照。
    // 编辑时先改 Controller，保存/重生成时再通过 _draftFromFields 合并回模型。
    final baseline = widget.aiBaseline;
    _session = EditorSessionState(
      draft: widget.draft,
      aiBaseline: baseline == null ? const {} : _baselineValues(baseline),
    );
    _titleController = TextEditingController(
      text: _draft.titleCandidates.isEmpty
          ? _draft.source.scenario
          : _draft.titleCandidates.first,
    );
    _bodyController = TextEditingController(text: _draft.body);
    _hashtagsController = TextEditingController(
      text: _draft.hashtags.join(' '),
    );
    _coverController = TextEditingController(text: _draft.coverCopy);
    if (baseline == null && widget.loadVersions != null) {
      _loadSavedBaseline();
    }
    if (widget.loadSuggestions != null) {
      unawaited(_loadSavedSuggestions());
    }
  }

  @override
  void dispose() {
    _titleController.dispose();
    _bodyController.dispose();
    _hashtagsController.dispose();
    _coverController.dispose();
    for (final node in _fieldFocusNodes.values) {
      node.dispose();
    }
    super.dispose();
  }

  Map<EditableField, Object> _baselineValues(NoteDraft draft) => {
    for (final field in EditableField.values)
      field: fieldValueForDraft(draft, field),
  };

  Future<void> _loadSavedSuggestions() async {
    try {
      final suggestions = await widget.loadSuggestions!(_draft.noteId);
      if (!mounted) return;
      var restored = _session;
      for (final suggestion in suggestions) {
        restored = restored.addSuggestion(
          suggestion,
          baseValue: fieldValueForDraft(_draft, suggestion.field),
        );
      }
      setState(() => _session = restored);
    } catch (_) {
      // The editor remains usable with session-only suggestions if history is unavailable.
    }
  }

  Future<void> _loadSavedBaseline() async {
    try {
      final versions = await widget.loadVersions!(_draft.noteId);
      if (!mounted || versions.isEmpty) return;
      final earliest = versions.reduce(
        (left, right) => left.version <= right.version ? left : right,
      );
      final baseline = _draft.copyWith(
        titleCandidates: earliest.titleCandidates,
        body: earliest.body,
        hashtags: earliest.hashtags,
        coverCopy: earliest.coverCopy,
        styleForm: earliest.styleForm ?? _draft.styleForm,
      );
      setState(() {
        _session = EditorSessionState(
          draft: _session.draft,
          aiBaseline: _baselineValues(baseline),
          pendingSuggestions: _session.pendingSuggestions,
        );
      });
    } catch (_) {
      // 没有可靠的历史基线时隐藏用户编辑 Diff，但不影响正常编辑。
    }
  }

  EditorSessionState _sessionWithControllers() {
    return EditorSessionState(
      draft: _draftFromFields(),
      aiBaseline: _session.aiBaseline,
      pendingSuggestions: _session.pendingSuggestions,
    );
  }

  void _syncControllersToSession() {
    _session = _sessionWithControllers();
  }

  NoteDraft _draftFromFields() {
    // 把用户当前正在编辑的文本重新组装成请求对象，避免保存旧的 _draft 快照。
    return _session.draft.copyWith(
      titleCandidates: [_titleController.text.trim()],
      body: _bodyController.text.trim(),
      hashtags: _hashtagsController.text
          .split(RegExp(r'\s+'))
          .where((tag) => tag.isNotEmpty)
          .toList(),
      coverCopy: _coverController.text.trim(),
    );
  }

  void _applyDraft(NoteDraft draft) {
    // 服务端返回新 draft 后，同时更新数据对象和四个 Controller，保持 UI 与模型一致。
    _session = EditorSessionState(
      draft: draft,
      aiBaseline: _session.aiBaseline,
      pendingSuggestions: _session.pendingSuggestions,
    );
    _titleController.text = draft.titleCandidates.isEmpty
        ? draft.source.scenario
        : draft.titleCandidates.first;
    _bodyController.text = draft.body;
    _hashtagsController.text = draft.hashtags.join(' ');
    _coverController.text = draft.coverCopy;
  }

  void _recordLocalVersion() {
    _localVersions.insert(
      0,
      _LocalVersion(
        label: '本机 v${_localVersions.length + 1}',
        title: _titleController.text,
        body: _bodyController.text,
        hashtags: _hashtagsController.text,
        coverCopy: _coverController.text,
      ),
    );
  }

  Future<void> _save() async {
    // 没有注入服务端保存函数时，退化为本机版本快照；有函数时才 PUT 到服务端。
    _syncControllersToSession();
    if (widget.onSaveDraft == null) {
      setState(_recordLocalVersion);
      _showSnackBar('已保存到本机草稿');
      return;
    }
    setState(() => _saving = true);
    try {
      final saved = await widget.onSaveDraft!(_draftFromFields());
      if (!mounted) return;
      setState(() {
        _applyDraft(saved);
        _recordLocalVersion();
      });
      _showSnackBar('草稿已保存');
    } catch (error) {
      if (mounted) _showSnackBar('保存失败：$error');
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  Future<void> _regenerate(String field) async {
    // 局部重生成返回独立候选；候选到达后不自动写入 Controller。
    final onRegenerate = widget.onRegenerateField;
    if (onRegenerate == null) {
      _showSnackBar('当前未接入局部重新生成');
      return;
    }
    final currentSession = _sessionWithControllers();
    final editableField = editableFieldFromApi(field);
    final baseValue = fieldValueForDraft(currentSession.draft, editableField);
    setState(() {
      _session = currentSession;
      _regeneratingField = field;
    });
    try {
      final suggestion = await onRegenerate(
        currentSession.draft,
        field,
        // 草稿列表重新打开时没有额外的页面参数，优先恢复服务端保存的表达形式。
        form: widget.styleForm ?? _draft.styleForm,
      );
      if (!mounted) return;
      // 候选到达后只进入 session/history，不写入 Controller；用户仍能继续编辑当前内容。
      setState(() {
        _session = _session.addSuggestion(suggestion, baseValue: baseValue);
      });
      _showSnackBar('已生成${_fieldLabel(field)}候选，请确认后采纳');
    } catch (error) {
      if (mounted) _showSnackBar('重新生成失败：$error');
    } finally {
      if (mounted) setState(() => _regeneratingField = null);
    }
  }

  Future<void> _acceptSuggestion(EditableField field) async {
    final current = _sessionWithControllers();
    final suggestion = current.suggestionFor(field);
    if (suggestion == null) return;
    if (current.hasConflict(suggestion)) {
      // 候选基于旧 digest 时必须先询问用户，避免异步响应覆盖刚刚完成的手动编辑。
      final choice = await showDialog<String>(
        context: context,
        builder: (context) => AlertDialog(
          title: Text('${_fieldLabel(editableFieldToApi(field))}已被修改'),
          content: const Text('AI 建议基于较早内容生成。请选择如何处理，不会自动覆盖你的修改。'),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context, 'keep'),
              child: const Text('保留当前内容'),
            ),
            OutlinedButton(
              onPressed: () => Navigator.pop(context, 'use'),
              child: const Text('使用 AI 候选'),
            ),
          ],
        ),
      );
      if (!mounted || choice == null) return;
      if (choice == 'keep') {
        setState(() {
          _session = current.rejectSuggestion(suggestion);
        });
        unawaited(_syncSuggestionStatus(suggestion, SuggestionStatus.rejected));
        return;
      }
      setState(() {
        _session = current.acceptSuggestion(suggestion, force: true);
        _writeDraftToControllers(_session.draft);
      });
      unawaited(_syncSuggestionStatus(suggestion, SuggestionStatus.accepted));
      return;
    }
    setState(() {
      _session = current.acceptSuggestion(suggestion);
      _writeDraftToControllers(_session.draft);
    });
    unawaited(_syncSuggestionStatus(suggestion, SuggestionStatus.accepted));
  }

  void _rejectSuggestion(EditableField field) {
    final suggestion = _session.suggestionFor(field);
    if (suggestion == null) return;
    setState(() {
      _session = _sessionWithControllers().rejectSuggestion(suggestion);
    });
    unawaited(_syncSuggestionStatus(suggestion, SuggestionStatus.rejected));
  }

  void _writeDraftToControllers(NoteDraft draft) {
    _titleController.text = draft.titleCandidates.isEmpty
        ? draft.source.scenario
        : draft.titleCandidates.first;
    _bodyController.text = draft.body;
    _hashtagsController.text = draft.hashtags.join(' ');
    _coverController.text = draft.coverCopy;
  }

  Future<void> _syncSuggestionStatus(
    FieldSuggestion suggestion,
    SuggestionStatus status,
  ) async {
    final callback = widget.onUpdateSuggestionStatus;
    if (callback == null) return;
    try {
      // 本地先完成采纳/拒绝，服务端同步失败只提示用户，不回滚编辑器里的明确选择。
      final synced = await callback(suggestion, status);
      if (!mounted) return;
      setState(() {
        _session = EditorSessionState(
          draft: _session.draft,
          aiBaseline: _session.aiBaseline,
          pendingSuggestions: _session.pendingSuggestions
              .map(
                (item) => item.suggestionId == synced.suggestionId
                    ? synced.copyWith(baseValue: item.baseValue)
                    : item,
              )
              .toList(),
        );
      });
    } catch (_) {
      if (mounted) _showSnackBar('候选状态同步失败，稍后可再次处理');
    }
  }

  String _fieldLabel(String field) {
    switch (field) {
      case 'title':
        return '标题';
      case 'body':
        return '正文';
      case 'hashtags':
        return '话题';
      case 'cover_copy':
        return '封面文案';
      default:
        return field;
    }
  }

  void _focusFinding(String? field) {
    if (field == null) return;
    final editableField = editableFieldFromApi(field);
    _fieldFocusNodes[editableField]?.requestFocus();
    final target = _fieldKeys[editableField]?.currentContext;
    if (target != null) {
      Scrollable.ensureVisible(
        target,
        duration: const Duration(milliseconds: 240),
      );
    }
  }

  Widget _diffText(FieldDiff diff) {
    return Wrap(
      children: [
        for (final segment in diff.segments)
          Tooltip(
            message: _diffRangeLabel(segment),
            child: Text(
              segment.text,
              style: TextStyle(
                color: switch (segment.kind) {
                  DiffSegmentKind.added => Colors.green.shade800,
                  DiffSegmentKind.removed => Colors.red.shade800,
                  DiffSegmentKind.unchanged => null,
                },
                decoration: segment.kind == DiffSegmentKind.removed
                    ? TextDecoration.lineThrough
                    : null,
              ),
            ),
          ),
      ],
    );
  }

  String _diffRangeLabel(DiffSegment segment) {
    final ranges = <String>[];
    if (segment.beforeStart != null && segment.beforeEnd != null) {
      ranges.add('原文 ${segment.beforeStart}–${segment.beforeEnd}');
    }
    if (segment.afterStart != null && segment.afterEnd != null) {
      ranges.add('建议 ${segment.afterStart}–${segment.afterEnd}');
    }
    return ranges.isEmpty ? '集合差异' : ranges.join('；');
  }

  Widget _baselineDiff(EditableField field) {
    final baseline = _session.aiBaseline[field];
    if (baseline == null) return const SizedBox.shrink();
    final current = fieldValueForDraft(_session.draft, field);
    final diff = diffFieldValues(
      field: field,
      before: baseline,
      after: current,
    );
    if (!diff.hasChanges) return const SizedBox.shrink();
    return Card(
      margin: const EdgeInsets.only(top: 8),
      color: Theme.of(context).colorScheme.surfaceContainerHighest,
      child: ExpansionTile(
        leading: const Icon(Icons.edit_note),
        title: const Text('查看 AI 初稿与当前编辑 Diff'),
        childrenPadding: const EdgeInsets.fromLTRB(16, 0, 16, 12),
        children: [_diffText(diff)],
      ),
    );
  }

  Widget _suggestionPanel(EditableField field) {
    final suggestion = _session.suggestionFor(field);
    final history = _session.suggestionsFor(field);
    if (suggestion == null && history.isEmpty) return const SizedBox.shrink();
    if (suggestion == null) return _suggestionHistory(field, history);
    final current = fieldValueForDraft(_session.draft, field);
    final diff = diffFieldValues(
      field: field,
      before: current,
      after: suggestion.value,
    );
    final review = suggestion.review;
    return Column(
      children: [
        Card(
          margin: const EdgeInsets.only(top: 8),
          color: Theme.of(context).colorScheme.primaryContainer,
          child: Padding(
            padding: const EdgeInsets.all(12),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('AI ${_fieldLabel(editableFieldToApi(field))}候选'),
                const SizedBox(height: 6),
                Text('当前内容 → AI 建议'),
                _diffText(diff),
                if (suggestion.evidence.isNotEmpty ||
                    suggestion.evidenceFactIds.isNotEmpty) ...[
                  const SizedBox(height: 8),
                  Text(
                    '来源证据：${[...suggestion.evidence, ...suggestion.evidenceFactIds].join('、')}',
                  ),
                ],
                if (review != null && !review.passed) ...[
                  const SizedBox(height: 8),
                  Text('候选需要复核：${review.findings.length} 项'),
                ],
                Row(
                  children: [
                    FilledButton(
                      onPressed: () => _acceptSuggestion(field),
                      child: const Text('采纳'),
                    ),
                    const SizedBox(width: 8),
                    TextButton(
                      onPressed: () => _rejectSuggestion(field),
                      child: const Text('拒绝'),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
        _suggestionHistory(field, history),
      ],
    );
  }

  Widget _suggestionHistory(
    EditableField field,
    List<FieldSuggestion> history,
  ) {
    if (history.isEmpty) return const SizedBox.shrink();
    return Card(
      margin: const EdgeInsets.only(top: 8),
      child: ExpansionTile(
        title: Text('${_fieldLabel(editableFieldToApi(field))}候选历史'),
        subtitle: Text('共 ${history.length} 条，只有 pending 可以采纳'),
        children: [
          for (final suggestion in history)
            ListTile(
              dense: true,
              title: Text(
                suggestion.textValue,
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
              ),
              subtitle: Text(_suggestionStatusLabel(suggestion.status)),
              trailing: suggestion.status == SuggestionStatus.stale
                  ? const Icon(Icons.warning_amber)
                  : null,
            ),
        ],
      ),
    );
  }

  String _suggestionStatusLabel(SuggestionStatus status) {
    switch (status) {
      case SuggestionStatus.pending:
        return '待处理';
      case SuggestionStatus.accepted:
        return '已采纳';
      case SuggestionStatus.rejected:
        return '已拒绝';
      case SuggestionStatus.stale:
        return '基础内容已变化';
    }
  }

  Future<void> _showVersions() async {
    // 版本历史有两条来源：服务端持久化版本 + 当前设备的本机快照。
    // 服务端读取失败时仍展示本机版本，保证编辑体验可用。
    var serverVersions = <NoteDraftVersion>[];
    if (widget.loadVersions != null) {
      try {
        serverVersions = await widget.loadVersions!(_draft.noteId);
      } catch (_) {
        // 版本读取失败时仍展示本机快照。
      }
    }
    if (!mounted) return;
    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      builder: (context) => DraggableScrollableSheet(
        expand: false,
        initialChildSize: 0.7,
        maxChildSize: 0.9,
        builder: (context, scrollController) => ListView(
          controller: scrollController,
          padding: const EdgeInsets.all(16),
          children: [
            Text('版本历史', style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 8),
            if (serverVersions.isEmpty && _localVersions.isEmpty)
              const ListTile(title: Text('还没有保存过版本'))
            else ...[
              for (final version in serverVersions.reversed)
                ListTile(
                  leading: const Icon(Icons.history),
                  title: Text('v${version.version}'),
                  subtitle: Text(
                    version.body.isEmpty
                        ? version.titleCandidates.join('、')
                        : version.body,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                  ),
                  trailing: const Icon(Icons.south_west),
                  onTap: () {
                    _restoreServerVersion(version);
                    Navigator.of(context).pop();
                  },
                ),
              for (final local in _localVersions)
                ListTile(
                  leading: const Icon(Icons.save_outlined),
                  title: Text(local.label),
                  subtitle: Text(
                    local.body.isEmpty ? local.title : local.body,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                  ),
                  trailing: const Icon(Icons.south_west),
                  onTap: () {
                    _titleController.text = local.title;
                    _bodyController.text = local.body;
                    _hashtagsController.text = local.hashtags;
                    _coverController.text = local.coverCopy;
                    _syncControllersToSession();
                    Navigator.of(context).pop();
                    _showSnackBar('已恢复 ${local.label}，保存后生效');
                  },
                ),
            ],
          ],
        ),
      ),
    );
  }

  void _restoreServerVersion(NoteDraftVersion version) {
    setState(() {
      final restored = _draft.copyWith(
        titleCandidates: version.titleCandidates.isEmpty
            ? _draft.titleCandidates
            : version.titleCandidates,
        body: version.body,
        hashtags: version.hashtags,
        coverCopy: version.coverCopy,
        styleForm: version.styleForm ?? _draft.styleForm,
      );
      _session = EditorSessionState(
        draft: restored,
        aiBaseline: _session.aiBaseline,
        pendingSuggestions: _session.pendingSuggestions
            .map(
              (suggestion) =>
                  suggestion.copyWith(status: SuggestionStatus.stale),
            )
            .toList(),
      );
      _writeDraftToControllers(restored);
    });
    _showSnackBar('已恢复 v${version.version}，保存后生效');
  }

  Future<void> _copy(String value, String label) async {
    // 复制是 V1 的手动发布边界：应用只写入系统剪贴板，不自动操作小红书。
    await Clipboard.setData(ClipboardData(text: value));
    if (mounted) {
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text('$label已复制')));
    }
  }

  void _showSnackBar(String message) {
    if (!mounted) return;
    ScaffoldMessenger.of(
      context,
    ).showSnackBar(SnackBar(content: Text(message)));
  }

  Widget _regenerateButton(String field, String label) {
    final busy = _regeneratingField == field;
    return TextButton.icon(
      onPressed: busy || _saving ? null : () => _regenerate(field),
      icon: busy
          ? const SizedBox.square(
              dimension: 14,
              child: CircularProgressIndicator(strokeWidth: 2),
            )
          : const Icon(Icons.refresh),
      label: Text(label),
    );
  }

  Widget _reviewBanner(BuildContext context) {
    if (_hasBlockingReview) {
      return Card(
        color: Theme.of(context).colorScheme.errorContainer,
        child: const ListTile(
          leading: Icon(Icons.block),
          title: Text('这篇内容需要修改后才能导出'),
          subtitle: Text('请检查疾病判断、用药或未经经历支持的表述。'),
        ),
      );
    }
    final warningFindings = _draft.reviewFindings
        .where((finding) => finding.level == RiskLevel.warning)
        .toList();
    if (warningFindings.isNotEmpty) {
      return Card(
        color: Theme.of(context).colorScheme.secondaryContainer,
        child: const ListTile(
          leading: Icon(Icons.info_outline),
          title: Text('有提示级问题，发布前请人工确认'),
        ),
      );
    }
    if (_needsReview) {
      return const Card(
        child: ListTile(
          leading: Icon(Icons.rate_review_outlined),
          title: Text('审核状态：待复核'),
          subtitle: Text('审核结果尚未通过，请确认内容后再继续使用。'),
        ),
      );
    }
    return const SizedBox.shrink();
  }

  String _traceLabel(AgentTraceStep step) {
    // 服务端 trace 使用稳定的机器 label；这里把它翻译成用户能看懂的中文阶段名。
    switch (step.label) {
      case 'load_style_profile':
        return '读取风格档案';
      case 'suggest_tags':
        return '生成话题建议';
      case 'critique_draft':
        return '自评草稿';
      case 'finalize_note':
        return '确认最终输出';
      case 'model':
        return '模型思考';
      case 'stub_fallback':
        return '未调用模型';
      default:
        return step.label;
    }
  }

  String _claimSupportLabel(ClaimSupport support) {
    switch (support) {
      case ClaimSupport.supported:
        return '有来源支持';
      case ClaimSupport.uncertain:
        return '来源不确定';
      case ClaimSupport.unsupported:
        return '未找到来源支持';
    }
  }

  @override
  Widget build(BuildContext context) {
    final reviewBanner = _reviewBanner(context);
    return Scaffold(
      appBar: AppBar(
        title: const Text('编辑笔记'),
        actions: [
          IconButton(
            tooltip: '版本历史',
            onPressed: _showVersions,
            icon: const Icon(Icons.history),
          ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          reviewBanner,
          if (widget.agentTrace.isNotEmpty)
            Card(
              child: ExpansionTile(
                leading: const Icon(Icons.psychology),
                title: const Text('Agent 执行过程'),
                subtitle: Text('共 ${widget.agentTrace.length} 步'),
                children: [
                  for (final step in widget.agentTrace)
                    ListTile(
                      dense: true,
                      leading: Icon(
                        step.kind == 'tool'
                            ? Icons.build_circle_outlined
                            : Icons.psychology_outlined,
                      ),
                      title: Text('${step.order}. ${_traceLabel(step)}'),
                      subtitle: Text(
                        step.summary,
                        maxLines: 3,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                ],
              ),
            ),
          Container(
            key: _fieldKeys[EditableField.title],
            child: TextField(
              controller: _titleController,
              focusNode: _fieldFocusNodes[EditableField.title],
              onChanged: (_) => setState(_syncControllersToSession),
              decoration: const InputDecoration(labelText: '标题'),
              maxLines: 2,
            ),
          ),
          Row(
            children: [
              TextButton.icon(
                onPressed: () => _copy(_titleController.text, '标题'),
                icon: const Icon(Icons.copy),
                label: const Text('复制标题'),
              ),
              _regenerateButton('title', '重新生成标题'),
            ],
          ),
          _baselineDiff(EditableField.title),
          _suggestionPanel(EditableField.title),
          const Divider(),
          Container(
            key: _fieldKeys[EditableField.body],
            child: TextField(
              controller: _bodyController,
              focusNode: _fieldFocusNodes[EditableField.body],
              onChanged: (_) => setState(_syncControllersToSession),
              decoration: const InputDecoration(labelText: '正文'),
              minLines: 5,
              maxLines: 12,
            ),
          ),
          Row(
            children: [
              TextButton.icon(
                onPressed: () => _copy(_bodyController.text, '正文'),
                icon: const Icon(Icons.copy),
                label: const Text('复制正文'),
              ),
              _regenerateButton('body', '重新生成正文'),
            ],
          ),
          _baselineDiff(EditableField.body),
          _suggestionPanel(EditableField.body),
          const Divider(),
          Container(
            key: _fieldKeys[EditableField.hashtags],
            child: TextField(
              controller: _hashtagsController,
              focusNode: _fieldFocusNodes[EditableField.hashtags],
              onChanged: (_) => setState(_syncControllersToSession),
              decoration: const InputDecoration(labelText: '话题'),
            ),
          ),
          Row(
            children: [
              TextButton.icon(
                onPressed: () => _copy(_hashtagsController.text, '话题'),
                icon: const Icon(Icons.copy),
                label: const Text('复制话题'),
              ),
              _regenerateButton('hashtags', '重新生成话题'),
            ],
          ),
          _baselineDiff(EditableField.hashtags),
          _suggestionPanel(EditableField.hashtags),
          const Divider(),
          Container(
            key: _fieldKeys[EditableField.coverCopy],
            child: TextField(
              controller: _coverController,
              focusNode: _fieldFocusNodes[EditableField.coverCopy],
              onChanged: (_) => setState(_syncControllersToSession),
              decoration: const InputDecoration(labelText: '封面文案'),
            ),
          ),
          _regenerateButton('cover_copy', '重新生成封面文案'),
          _baselineDiff(EditableField.coverCopy),
          _suggestionPanel(EditableField.coverCopy),
          if (_draft.imageSuggestions.isNotEmpty)
            ListTile(
              contentPadding: EdgeInsets.zero,
              title: const Text('配图建议'),
              subtitle: Text(_draft.imageSuggestions.join('、')),
            ),
          if (_draft.reviewFindings.isNotEmpty)
            ..._draft.reviewFindings.map(
              (finding) => ListTile(
                contentPadding: EdgeInsets.zero,
                leading: Icon(
                  finding.level == RiskLevel.blocking
                      ? Icons.block
                      : Icons.info_outline,
                ),
                title: Text(finding.message),
                subtitle: finding.matchedText == null
                    ? null
                    : Text('命中：${finding.matchedText}'),
                onTap: finding.field == null
                    ? null
                    : () => _focusFinding(finding.field),
              ),
            ),
          if (_draft.review != null)
            ..._draft.review!.claimAudit
                .where((item) => item.support != ClaimSupport.supported)
                .map(
                  (item) => ListTile(
                    contentPadding: EdgeInsets.zero,
                    leading: Icon(
                      item.level == RiskLevel.blocking
                          ? Icons.block
                          : Icons.info_outline,
                    ),
                    title: Text(_claimSupportLabel(item.support)),
                    subtitle: Text(
                      item.reason.isEmpty
                          ? item.claim
                          : '${item.claim}\n${item.reason}',
                    ),
                  ),
                ),
          const SizedBox(height: 12),
          Row(
            children: [
              Expanded(
                child: FilledButton.icon(
                  onPressed: _saving ? null : _save,
                  icon: _saving
                      ? const SizedBox.square(
                          dimension: 16,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Icon(Icons.save_outlined),
                  label: Text(_saving ? '保存中…' : '保存草稿'),
                ),
              ),
              if (widget.onPublish != null) ...[
                const SizedBox(width: 12),
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: widget.onPublish,
                    icon: const Icon(Icons.check_circle_outline),
                    label: const Text('记录发布结果'),
                  ),
                ),
              ],
            ],
          ),
        ],
      ),
    );
  }
}
