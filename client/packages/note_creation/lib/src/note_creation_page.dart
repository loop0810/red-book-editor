import 'dart:io';

import 'package:app_core/app_core.dart';
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';

import 'note_creation_types.dart';
import 'note_editor_page.dart';

class NoteCreationPage extends StatefulWidget {
  const NoteCreationPage({
    required this.generate,
    this.uploadAsset,
    this.onDraftGenerated,
    super.key,
  });

  final GenerateNote generate;
  final UploadAsset? uploadAsset;
  final Future<void> Function(NoteDraft draft)? onDraftGenerated;

  @override
  State<NoteCreationPage> createState() => _NoteCreationPageState();
}

class _NoteCreationPageState extends State<NoteCreationPage> {
  final _scenarioController = TextEditingController();
  final _actionsController = TextEditingController();
  final _observationsController = TextEditingController();
  final _notesController = TextEditingController();
  final _picker = ImagePicker();
  final _pickedPaths = <String>[];
  int _babyMonth = 19;
  bool _loading = false;
  String? _error;
  final _draftStore = SourceExperienceDraftStore();

  @override
  void initState() {
    super.initState();
    _restoreDraft();
  }

  Future<void> _restoreDraft() async {
    final draft = await _draftStore.load();
    if (!mounted || draft == null) return;
    _scenarioController.text = draft.scenario;
    _actionsController.text = draft.actions.join('，');
    _observationsController.text = draft.observations;
    _notesController.text = draft.notes;
    setState(() {
      _babyMonth = draft.babyMonth;
      _pickedPaths
        ..clear()
        ..addAll(draft.assetIds);
    });
  }

  Future<void> _pickImages() async {
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
    _scenarioController.dispose();
    _actionsController.dispose();
    _observationsController.dispose();
    _notesController.dispose();
    super.dispose();
  }

  Future<void> _generate() async {
    if (_scenarioController.text.trim().isEmpty ||
        _actionsController.text.trim().isEmpty) {
      setState(() => _error = '请先填写发生了什么和你做了什么');
      return;
    }
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final assetIds = <String>[];
      for (final path in _pickedPaths) {
        if (widget.uploadAsset == null) {
          assetIds.add(path);
          continue;
        }
        assetIds.add(await widget.uploadAsset!(path));
      }
      final source = SourceExperience(
        babyMonth: _babyMonth,
        scenario: _scenarioController.text.trim(),
        actions: _actionsController.text
            .split(RegExp(r'[,，\n]'))
            .map((action) => action.trim())
            .where((action) => action.isNotEmpty)
            .toList(),
        observations: _observationsController.text.trim(),
        notes: _notesController.text.trim(),
        assetIds: assetIds,
      );
      await _draftStore.save(source);
      final draft = await widget.generate(source);
      await _draftStore.clear();
      if (mounted) {
        if (widget.onDraftGenerated != null) {
          await widget.onDraftGenerated!(draft);
        } else {
          await Navigator.of(context).push(
            MaterialPageRoute(builder: (_) => NoteEditorPage(draft: draft)),
          );
        }
      }
    } catch (error) {
      if (mounted) setState(() => _error = '生成失败：$error');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('记录一次育儿经历')),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          Text('宝宝月龄：$_babyMonth 个月'),
          Slider(
            value: _babyMonth.toDouble(),
            min: 0,
            max: 24,
            divisions: 24,
            onChanged: (value) => setState(() => _babyMonth = value.round()),
          ),
          TextField(
            controller: _scenarioController,
            decoration: const InputDecoration(labelText: '发生了什么'),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _actionsController,
            maxLines: 3,
            decoration: const InputDecoration(labelText: '我做了什么（可用逗号分隔）'),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _observationsController,
            maxLines: 3,
            decoration: const InputDecoration(labelText: '观察到什么变化'),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _notesController,
            maxLines: 3,
            decoration: const InputDecoration(labelText: '补充说明'),
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
        ],
      ),
    );
  }
}
