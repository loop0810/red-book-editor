import 'dart:io';

import 'package:app_core/app_core.dart';
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';

import 'note_creation_types.dart';
import 'note_editor_page.dart';

class NoteCreationPage extends StatefulWidget {
  // 页面只负责收集输入和管理交互；真正的生成函数由外层 main.dart 注入。
  // 这样 feature package 不需要知道 API Client 或具体网络实现。
  const NoteCreationPage({
    required this.generate,
    this.generateWithProgress,
    this.resumeAgentRun,
    this.cancelAgentRun,
    this.uploadAsset,
    this.onDraftGenerated,
    super.key,
  });

  final GenerateNote generate;
  final GenerateNoteWithProgress? generateWithProgress;
  final ResumeAgentRun? resumeAgentRun;
  final CancelAgentRun? cancelAgentRun;
  final UploadAsset? uploadAsset;
  final Future<void> Function(StyledNoteResponse response, StyleForm form)?
  onDraftGenerated;

  @override
  State<NoteCreationPage> createState() => _NoteCreationPageState();
}

class _NoteCreationPageState extends State<NoteCreationPage> {
  // Controller 保存输入框内容，_draftStore 保存“请求尚未完成时”的本地草稿。
  final _focusController = TextEditingController();
  final _rawMaterialController = TextEditingController();
  final _picker = ImagePicker();
  final _pickedPaths = <String>[];
  StyleForm _selectedForm = StyleForm.experience;
  bool _loading = false;
  String? _error;
  String? _activeRunId;
  String? _failedRunId;
  StyleForm? _lastForm;
  final _contentBriefStore = ContentBriefDraftStore();
  final _legacyDraftStore = SourceExperienceDraftStore();

  @override
  void initState() {
    super.initState();
    // 页面重新打开时只恢复标题和正文，避免把旧的育儿拆分表单重新带回页面。
    _restoreDraft();
  }

  Future<void> _restoreDraft() async {
    var draft = await _contentBriefStore.load();
    if (draft == null) {
      final legacy = await _legacyDraftStore.load();
      if (legacy != null) draft = ContentBrief.fromLegacy(legacy);
    }
    if (!mounted || draft == null) return;
    final restored = draft;
    _focusController.text = restored.focus;
    _rawMaterialController.text = restored.rawMaterial;
    setState(
      () => _pickedPaths
        ..clear()
        ..addAll(restored.assetIds),
    );
  }

  Future<void> _pickImages() async {
    // 图片此时只有本地路径；点击生成时才会通过 widget.uploadAsset 上传到服务端。
    final picked = await _picker.pickMultiImage(imageQuality: 90);
    if (!mounted) return;
    setState(() {
      _pickedPaths.addAll(picked.map((file) => file.path));
    });
  }

  void _removeImage(int index) {
    setState(() => _pickedPaths.removeAt(index));
  }

  @override
  void dispose() {
    _focusController.dispose();
    _rawMaterialController.dispose();
    super.dispose();
  }

  Future<void> _generate() async {
    // 生成主链路：校验输入 → 上传素材 → 组装 ContentBrief → 保存本地草稿 → 请求服务端。
    // 在请求成功前不清除本地草稿，避免网络或模型失败导致用户输入丢失。
    final focus = _focusController.text.trim().isNotEmpty
        ? _focusController.text.trim()
        : '';
    final rawMaterial = _rawMaterialController.text.trim().isNotEmpty
        ? _rawMaterialController.text.trim()
        : '';
    if (focus.isEmpty || rawMaterial.isEmpty) {
      setState(() => _error = '请先填写内容主题和内容素材');
      return;
    }
    setState(() {
      _loading = true;
      _error = null;
    });
    String? runIdForRecovery;
    try {
      final assetIds = <String>[];
      for (final path in _pickedPaths) {
        if (widget.uploadAsset == null) {
          assetIds.add(path);
          continue;
        }
        assetIds.add(await widget.uploadAsset!(path));
      }
      final brief = ContentBrief(
        focus: focus,
        rawMaterial: rawMaterial,
        assetIds: assetIds,
      );
      _lastForm = _selectedForm;
      _failedRunId = null;
      await _contentBriefStore.save(brief);
      // generate 是依赖注入进来的 Future：测试时可以替换成 fake，生产时由 API Client 实现。
      final response = widget.generateWithProgress == null
          ? await widget.generate(brief, _selectedForm)
          : await widget.generateWithProgress!(
              brief,
              _selectedForm,
              onRunCreated: (run) {
                if (!mounted) return;
                runIdForRecovery = run.runId;
                _activeRunId = run.runId;
              },
            );
      await _contentBriefStore.clear();
      await _legacyDraftStore.clear();
      _failedRunId = null;
      await _openGeneratedNote(response, _selectedForm);
    } catch (error) {
      if (mounted) setState(() => _error = '生成失败：$error');
    } finally {
      if (mounted) {
        setState(() {
          _loading = false;
          _failedRunId ??= runIdForRecovery ?? _activeRunId;
          _activeRunId = null;
        });
      }
    }
  }

  Future<void> _openGeneratedNote(
    StyledNoteResponse response,
    StyleForm form,
  ) async {
    // 只有服务端生成成功才进入编辑器；内部运行摘要不属于主创作页面。
    if (!mounted) return;
    if (widget.onDraftGenerated != null) {
      await widget.onDraftGenerated!(response, form);
    } else {
      await Navigator.of(context).push(
        MaterialPageRoute(
          builder: (_) => NoteEditorPage(
            draft: response.draft,
            aiBaseline: response.draft,
            styleForm: form,
          ),
        ),
      );
    }
  }

  Future<void> _resumeGeneration() async {
    final runId = _failedRunId;
    final resume = widget.resumeAgentRun;
    if (runId == null || resume == null) {
      _showRecoveryMessage('当前无法继续运行，请点击重新生成');
      return;
    }
    setState(() {
      _loading = true;
      _error = null;
      _failedRunId = null;
    });
    try {
      final response = await resume(
        runId,
        onRunCreated: (run) {
          if (!mounted) return;
          _activeRunId = run.runId;
        },
      );
      await _contentBriefStore.clear();
      await _legacyDraftStore.clear();
      _failedRunId = null;
      await _openGeneratedNote(response, _lastForm ?? _selectedForm);
    } catch (error) {
      if (mounted) {
        setState(() {
          _error = '继续运行失败：$error';
          _failedRunId = runId;
        });
      }
    } finally {
      if (mounted) {
        setState(() {
          _loading = false;
          _activeRunId = null;
        });
      }
    }
  }

  void _showRecoveryMessage(String message) {
    if (mounted) setState(() => _error = message);
  }

  Future<void> _cancelGeneration() async {
    final runId = _activeRunId;
    if (runId == null || widget.cancelAgentRun == null) return;
    try {
      await widget.cancelAgentRun!(runId);
      if (mounted) setState(() => _error = '已请求取消生成');
    } catch (error) {
      if (mounted) setState(() => _error = '取消失败：$error');
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('新建内容')),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          Text('标题', style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 8),
          TextField(
            controller: _focusController,
            decoration: const InputDecoration(
              labelText: '内容主题',
              hintText: '例如：宝宝周岁宴',
            ),
          ),
          const SizedBox(height: 12),
          Text('正文', style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 8),
          TextField(
            controller: _rawMaterialController,
            maxLines: 5,
            decoration: const InputDecoration(
              labelText: '内容素材',
              hintText: '关键词、流水账、几句话都可以，不需要先写成完整文案',
            ),
          ),
          const SizedBox(height: 16),
          Row(
            children: [
              OutlinedButton.icon(
                onPressed: _pickImages,
                icon: const Icon(Icons.photo_library),
                label: const Text('选择图片（可选）'),
              ),
              if (_pickedPaths.isNotEmpty)
                Padding(
                  padding: const EdgeInsets.only(left: 12),
                  child: Text('已选 ${_pickedPaths.length} 张'),
                ),
            ],
          ),
          if (_pickedPaths.isNotEmpty) ...[
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                for (var index = 0; index < _pickedPaths.length; index++)
                  Stack(
                    children: [
                      ClipRRect(
                        borderRadius: BorderRadius.circular(8),
                        child: Image.file(
                          File(_pickedPaths[index]),
                          width: 80,
                          height: 80,
                          fit: BoxFit.cover,
                          errorBuilder: (_, _, _) => const SizedBox.square(
                            dimension: 80,
                            child: Icon(Icons.image),
                          ),
                        ),
                      ),
                      Positioned(
                        top: 0,
                        right: 0,
                        child: InkWell(
                          onTap: () => _removeImage(index),
                          child: Container(
                            decoration: const BoxDecoration(
                              color: Colors.black54,
                              shape: BoxShape.circle,
                            ),
                            child: const Icon(
                              Icons.close,
                              size: 16,
                              color: Colors.white,
                            ),
                          ),
                        ),
                      ),
                    ],
                  ),
              ],
            ),
          ],
          if (_error != null) ...[
            const SizedBox(height: 12),
            Text(
              _error!,
              style: TextStyle(color: Theme.of(context).colorScheme.error),
            ),
          ],
          const SizedBox(height: 16),
          Text('表达形式', style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 8),
          SegmentedButton<StyleForm>(
            segments: const [
              ButtonSegment(value: StyleForm.popularScience, label: Text('科普')),
              ButtonSegment(value: StyleForm.experience, label: Text('经验')),
              ButtonSegment(value: StyleForm.advertorial, label: Text('软文')),
            ],
            selected: {_selectedForm},
            onSelectionChanged: (selection) {
              setState(() => _selectedForm = selection.first);
            },
          ),
          const SizedBox(height: 24),
          FilledButton.icon(
            onPressed: _loading ? null : _generate,
            icon: _loading
                ? const SizedBox.square(
                    dimension: 16,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Icon(Icons.auto_awesome),
            label: Text(_loading ? '生成中…' : '生成笔记'),
          ),
          if (!_loading && _failedRunId != null) ...[
            const SizedBox(height: 12),
            Card(
              child: ListTile(
                leading: const Icon(Icons.restart_alt),
                title: const Text('这次生成没有完成'),
                subtitle: const Text('可以继续原来的运行，或重新开始一次生成。'),
                trailing: Wrap(
                  spacing: 4,
                  children: [
                    if (widget.resumeAgentRun != null)
                      TextButton(
                        onPressed: _resumeGeneration,
                        child: const Text('继续运行'),
                      ),
                    TextButton(
                      onPressed: _loading ? null : _generate,
                      child: const Text('重新生成'),
                    ),
                  ],
                ),
              ),
            ),
          ],
          if (_loading && widget.generateWithProgress != null) ...[
            const SizedBox(height: 12),
            if (_activeRunId != null && widget.cancelAgentRun != null)
              TextButton.icon(
                onPressed: _cancelGeneration,
                icon: const Icon(Icons.stop_circle_outlined),
                label: const Text('取消生成'),
              ),
          ],
        ],
      ),
    );
  }
}
