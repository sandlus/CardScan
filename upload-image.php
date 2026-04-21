<?php

header("Content-Type: application/json");

// ✅ Absolute path
$targetDir = __DIR__ . "/uploads/images/";

// ensure folder exists
if (!file_exists($targetDir)) {
    mkdir($targetDir, 0777, true);
}

// check file exists
if (!isset($_FILES['image'])) {
    echo json_encode([
        "status" => false,
        "message" => "No image received"
    ]);
    exit;
}

$file = $_FILES['image'];

// ✅ check upload error
if ($file["error"] !== UPLOAD_ERR_OK) {
    echo json_encode([
        "status" => false,
        "message" => "Upload error",
        "error_code" => $file["error"]
    ]);
    exit;
}

// ✅ STEP 3: extension fallback
$extension = strtolower(pathinfo($file["name"], PATHINFO_EXTENSION));
if (!$extension) {
    $extension = "jpg";
}

// ✅ STEP 2: allowed extensions
$allowed = ['jpg', 'jpeg', 'png'];
if (!in_array($extension, $allowed)) {
    echo json_encode([
        "status" => false,
        "message" => "Invalid file type"
    ]);
    exit;
}

// ✅ EXTRA: MIME type validation (VERY IMPORTANT)
$finfo = finfo_open(FILEINFO_MIME_TYPE);
$mime = finfo_file($finfo, $file["tmp_name"]);
finfo_close($finfo);

$allowedMime = ['image/jpeg', 'image/png'];
if (!in_array($mime, $allowedMime)) {
    echo json_encode([
        "status" => false,
        "message" => "Invalid MIME type"
    ]);
    exit;
}

// ✅ STEP 4: file size limit (5MB)
if ($file["size"] > 5 * 1024 * 1024) {
    echo json_encode([
        "status" => false,
        "message" => "File too large (Max 5MB)"
    ]);
    exit;
}

// ✅ generate safe filename
$filename = time() . "_front_" . bin2hex(random_bytes(5)) . "." . $extension;

$targetFile = $targetDir . $filename;

// move file
if (move_uploaded_file($file["tmp_name"], $targetFile)) {

    $url = "https://demoapp.sandlus.in/uploads/images/" . $filename;

    echo json_encode([
        "status" => true,
        "filename" => $filename,
        "url" => $url
    ]);
} else {

    echo json_encode([
        "status" => false,
        "message" => "Failed to upload",
        "debug" => error_get_last()
    ]);
}