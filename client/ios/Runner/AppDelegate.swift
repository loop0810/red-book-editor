import Flutter
import Photos
import UIKit

@main
@objc class AppDelegate: FlutterAppDelegate, FlutterImplicitEngineDelegate {
  override func application(
    _ application: UIApplication,
    didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?
  ) -> Bool {
    return super.application(application, didFinishLaunchingWithOptions: launchOptions)
  }

  func didInitializeImplicitFlutterEngine(_ engineBridge: FlutterImplicitEngineBridge) {
    GeneratedPluginRegistrant.register(with: engineBridge.pluginRegistry)
    let channel = FlutterMethodChannel(
      name: "red_book_editor/gallery",
      binaryMessenger: engineBridge.applicationRegistrar.messenger()
    )
    channel.setMethodCallHandler { call, result in
      guard call.method == "saveImage" else {
        result(FlutterMethodNotImplemented)
        return
      }
      guard
        let arguments = call.arguments as? [String: Any],
        let data = arguments["bytes"] as? FlutterStandardTypedData,
        let filename = arguments["filename"] as? String
      else {
        result(
          FlutterError(
            code: "invalid_arguments",
            message: "Missing bytes or filename",
            details: nil
          )
        )
        return
      }
      PHPhotoLibrary.shared().performChanges({
        let request = PHAssetCreationRequest.forAsset()
        let options = PHAssetResourceCreationOptions()
        options.originalFilename = filename
        request.addResource(with: .photo, data: data.data, options: options)
      }) { success, error in
        if success {
          result(nil)
        } else {
          result(
            FlutterError(
              code: "save_failed",
              message: error?.localizedDescription ?? "Save failed",
              details: nil
            )
          )
        }
      }
    }
  }
}
