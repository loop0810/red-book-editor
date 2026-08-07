import 'dart:typed_data';

import 'package:app_core/app_core.dart';
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';

typedef ListAssets = Future<List<Asset>> Function();
typedef UploadAssetWithProgress =
    Future<String> Function(
      String filePath,
      void Function(int sentBytes, int totalBytes)? onProgress,
    );
typedef DeleteAsset = Future<void> Function(String assetId);
typedef ReorderAssets = Future<List<Asset>> Function(List<String> assetIds);
typedef DownloadAsset = Future<DownloadedAsset> Function(String assetId);
typedef ExportImage = Future<void> Function(Uint8List bytes, String filename);

class AssetLibraryPage extends StatefulWidget {
  const AssetLibraryPage({
    required this.listAssets,
    required this.uploadAsset,
    required this.deleteAsset,
    required this.reorderAssets,
    required this.downloadAsset,
    required this.exportImage,
    super.key,
  });

  final ListAssets listAssets;
  final UploadAssetWithProgress uploadAsset;
  final DeleteAsset deleteAsset;
  final ReorderAssets reorderAssets;
  final DownloadAsset downloadAsset;
  final ExportImage exportImage;

  @override
  State<AssetLibraryPage> createState() => _AssetLibraryPageState();
}

class _AssetLibraryPageState extends State<AssetLibraryPage> {
  final _picker = ImagePicker();
  List<Asset> _assets = [];
  final _previews = <String, Uint8List>{};
  final _uploadProgress = <String, double>{};
  bool _loading = true;
  bool _exporting = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final assets = await widget.listAssets();
      if (mounted) setState(() => _assets = assets);
    } catch (error) {
      if (mounted) setState(() => _error = '素材列表加载失败：$error');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<Uint8List?> _previewFor(Asset asset) async {
    final cached = _previews[asset.assetId];
    if (cached != null) return cached;
    try {
      final downloaded = await widget.downloadAsset(asset.assetId);
      if (mounted) setState(() => _previews[asset.assetId] = downloaded.bytes);
      return downloaded.bytes;
    } catch (_) {
      return null;
    }
  }

  Future<void> _pickAndUpload() async {
    final picked = await _picker.pickMultiImage(imageQuality: 90);
    if (picked.isEmpty) return;
    for (final file in picked) {
      setState(() => _uploadProgress[file.path] = 0);
      try {
        await widget.uploadAsset(file.path, (sent, total) {
          if (!mounted) return;
          setState(() {
            _uploadProgress[file.path] = total == 0 ? 0 : sent / total;
          });
        });
      } catch (error) {
        if (mounted) {
          ScaffoldMessenger.of(
            context,
          ).showSnackBar(SnackBar(content: Text('${file.name} 上传失败：$error')));
        }
      }
      if (mounted) setState(() => _uploadProgress.remove(file.path));
    }
    await _load();
  }

  Future<void> _delete(Asset asset) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('删除素材'),
        content: Text('确定删除「${asset.filename}」吗？删除后不可恢复。'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('取消'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(context).pop(true),
            child: const Text('删除'),
          ),
        ],
      ),
    );
    if (confirmed != true) return;
    try {
      await widget.deleteAsset(asset.assetId);
      if (mounted) {
        setState(() {
          _assets = _assets
              .where((item) => item.assetId != asset.assetId)
              .toList();
          _previews.remove(asset.assetId);
        });
      }
    } catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text('删除失败：$error')));
      }
    }
  }

  Future<void> _move(Asset asset, int delta) async {
    final index = _assets.indexWhere((item) => item.assetId == asset.assetId);
    final target = index + delta;
    if (index < 0 || target < 0 || target >= _assets.length) return;
    final reordered = [..._assets];
    final item = reordered.removeAt(index);
    reordered.insert(target, item);
    setState(() => _assets = reordered);
    try {
      final saved = await widget.reorderAssets(
        reordered.map((asset) => asset.assetId).toList(),
      );
      if (mounted) setState(() => _assets = saved);
    } catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text('排序保存失败：$error')));
        _load();
      }
    }
  }

  Future<void> _exportAll() async {
    if (_assets.isEmpty || _exporting) return;
    setState(() => _exporting = true);
    var exported = 0;
    var failed = 0;
    for (var index = 0; index < _assets.length; index++) {
      final asset = _assets[index];
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('正在导出 ${index + 1}/${_assets.length}')),
      );
      try {
        final downloaded = await widget.downloadAsset(asset.assetId);
        await widget.exportImage(downloaded.bytes, downloaded.filename);
        exported++;
      } catch (_) {
        failed++;
      }
    }
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            failed == 0
                ? '已导出 $exported 张图片到相册'
                : '已导出 $exported 张，失败 $failed 张',
          ),
        ),
      );
      setState(() => _exporting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('图片素材')),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.all(16),
            child: Row(
              children: [
                OutlinedButton.icon(
                  onPressed: _pickAndUpload,
                  icon: const Icon(Icons.photo_library),
                  label: const Text('选择并上传'),
                ),
                const SizedBox(width: 12),
                FilledButton.icon(
                  onPressed: _exporting || _assets.isEmpty ? null : _exportAll,
                  icon: _exporting
                      ? const SizedBox.square(
                          dimension: 16,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Icon(Icons.download_done),
                  label: Text(_exporting ? '导出中…' : '全部导出到相册'),
                ),
              ],
            ),
          ),
          if (_error != null)
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: Text(
                _error!,
                style: TextStyle(color: Theme.of(context).colorScheme.error),
              ),
            ),
          if (_uploadProgress.isNotEmpty)
            ..._uploadProgress.entries.map(
              (entry) => Padding(
                padding: const EdgeInsets.symmetric(
                  horizontal: 16,
                  vertical: 4,
                ),
                child: LinearProgressIndicator(
                  value: entry.value,
                  minHeight: 4,
                ),
              ),
            ),
          Expanded(
            child: _loading
                ? const Center(child: CircularProgressIndicator())
                : GridView.builder(
                    padding: const EdgeInsets.all(16),
                    gridDelegate:
                        const SliverGridDelegateWithFixedCrossAxisCount(
                          crossAxisCount: 3,
                          crossAxisSpacing: 8,
                          mainAxisSpacing: 8,
                        ),
                    itemCount: _assets.length,
                    itemBuilder: (context, index) => _AssetTile(
                      asset: _assets[index],
                      first: index == 0,
                      last: index == _assets.length - 1,
                      onPreview: () => _previewFor(_assets[index]),
                      onDelete: () => _delete(_assets[index]),
                      onMoveLeft: () => _move(_assets[index], -1),
                      onMoveRight: () => _move(_assets[index], 1),
                    ),
                  ),
          ),
        ],
      ),
    );
  }
}

class _AssetTile extends StatelessWidget {
  const _AssetTile({
    required this.asset,
    required this.first,
    required this.last,
    required this.onPreview,
    required this.onDelete,
    required this.onMoveLeft,
    required this.onMoveRight,
  });

  final Asset asset;
  final bool first;
  final bool last;
  final Future<Uint8List?> Function() onPreview;
  final VoidCallback onDelete;
  final VoidCallback onMoveLeft;
  final VoidCallback onMoveRight;

  @override
  Widget build(BuildContext context) {
    return Stack(
      fit: StackFit.expand,
      children: [
        ClipRRect(
          borderRadius: BorderRadius.circular(8),
          child: FutureBuilder<Uint8List?>(
            future: onPreview(),
            builder: (context, snapshot) {
              final bytes = snapshot.data;
              if (bytes == null) {
                return Container(
                  color: Theme.of(context).colorScheme.surfaceContainerHighest,
                  child: const Icon(Icons.image),
                );
              }
              return Image.memory(bytes, fit: BoxFit.cover);
            },
          ),
        ),
        Positioned(
          top: 2,
          right: 2,
          child: InkWell(
            onTap: onDelete,
            child: Container(
              decoration: const BoxDecoration(
                color: Colors.black54,
                shape: BoxShape.circle,
              ),
              child: const Icon(Icons.close, size: 16, color: Colors.white),
            ),
          ),
        ),
        Positioned(
          left: 2,
          bottom: 2,
          child: IconButton(
            visualDensity: VisualDensity.compact,
            onPressed: first ? null : onMoveLeft,
            icon: const Icon(Icons.arrow_back, size: 16, color: Colors.white),
          ),
        ),
        Positioned(
          right: 2,
          bottom: 2,
          child: IconButton(
            visualDensity: VisualDensity.compact,
            onPressed: last ? null : onMoveRight,
            icon: const Icon(
              Icons.arrow_forward,
              size: 16,
              color: Colors.white,
            ),
          ),
        ),
      ],
    );
  }
}
