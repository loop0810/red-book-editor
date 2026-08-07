import 'package:app_core/app_core.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import 'note_creation_types.dart';

class NoteEditorPage extends StatefulWidget {
  const NoteEditorPage({
    required this.draft,
    this.onPublish,
    this.onRegenerateField,
    this.onSaveDraft,
    this.loadVersions,
    super.key,
  });

  final NoteDraft draft;
  final Future<void> Function()? onPublish;
  final RegenerateField? onRegenerateField;
  final SaveDraft? onSaveDraft;
  final LoadVersions? loadVersions;

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
  late NoteDraft _draft;
  late final TextEditingController _titleController;
  late final TextEditingController _bodyController;
  late final TextEditingController _hashtagsController;
  late final TextEditingController _coverController;
  final _localVersions = <_LocalVersion>[];
  bool _saving = false;
  String? _regeneratingField;

  bool get _hasBlockingReview => _draft.reviewFindings.any(
    (finding) => finding.level == RiskLevel.blocking,
  );

  @override
  void initState() {
    super.initState();
    _draft = widget.draft;
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
  }

  @override
  void dispose() {
    _titleController.dispose();
    _bodyController.dispose();
    _hashtagsController.dispose();
    _coverController.dispose();
    super.dispose();
  }

  NoteDraft _draftFromFields() {
    return _draft.copyWith(
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
    _draft = draft;
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
    final onRegenerate = widget.onRegenerateField;
    if (onRegenerate == null) {
      _showSnackBar('当前未接入局部重新生成');
      return;
    }
    setState(() => _regeneratingField = field);
    try {
      final regenerated = await onRegenerate(_draftFromFields(), field);
      if (!mounted) return;
      setState(() => _applyDraft(regenerated));
      _showSnackBar('已重新生成${_fieldLabel(field)}');
    } catch (error) {
      if (mounted) _showSnackBar('重新生成失败：$error');
    } finally {
      if (mounted) setState(() => _regeneratingField = null);
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

  Future<void> _showVersions() async {
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
      _draft = _draft.copyWith(
        titleCandidates: version.titleCandidates.isEmpty
            ? _draft.titleCandidates
            : version.titleCandidates,
        body: version.body,
        hashtags: version.hashtags,
        coverCopy: version.coverCopy,
      );
      _titleController.text = version.titleCandidates.isEmpty
          ? _draft.source.scenario
          : version.titleCandidates.first;
      _bodyController.text = version.body;
      _hashtagsController.text = version.hashtags.join(' ');
      _coverController.text = version.coverCopy;
    });
    _showSnackBar('已恢复 v${version.version}，保存后生效');
  }

  Future<void> _copy(String value, String label) async {
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

  @override
  Widget build(BuildContext context) {
    final warningFindings = _draft.reviewFindings
        .where((finding) => finding.level == RiskLevel.warning)
        .toList();
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
          if (_hasBlockingReview)
            Card(
              color: Theme.of(context).colorScheme.errorContainer,
              child: const ListTile(
                leading: Icon(Icons.block),
                title: Text('这篇内容需要修改后才能导出'),
                subtitle: Text('请检查疾病判断、用药或未经经历支持的表述。'),
              ),
            )
          else if (warningFindings.isNotEmpty)
            Card(
              color: Theme.of(context).colorScheme.secondaryContainer,
              child: const ListTile(
                leading: Icon(Icons.info_outline),
                title: Text('有提示级问题，发布前请人工确认'),
              ),
            ),
          TextField(
            controller: _titleController,
            decoration: const InputDecoration(labelText: '标题'),
            maxLines: 2,
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
          const Divider(),
          TextField(
            controller: _bodyController,
            decoration: const InputDecoration(labelText: '正文'),
            minLines: 5,
            maxLines: 12,
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
          const Divider(),
          TextField(
            controller: _hashtagsController,
            decoration: const InputDecoration(labelText: '话题'),
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
          const Divider(),
          TextField(
            controller: _coverController,
            decoration: const InputDecoration(labelText: '封面文案'),
          ),
          _regenerateButton('cover_copy', '重新生成封面文案'),
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
