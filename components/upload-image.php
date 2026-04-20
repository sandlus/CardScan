<?php

header("Content-Type: application/json");

// ✅ FIX: use absolute path
$targetDir = __DIR__ . "/uploads/images/";

// ensure folder exists
if (!file_exists($targetDir)) {
    mkdir($targetDir, 0777, true);
}

// check file
if (!isset($_FILES['image'])) {
    echo json_encode([
        "status" => false,
        "message" => "No image received"
    ]);
    exit;
}

$file = $_FILES['image'];

// safe extension handling
$extension = strtolower(pathinfo($file["name"], PATHINFO_EXTENSION));

// generate unique filename
$filename = time() . "_front_" . uniqid() . "." . $extension;

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