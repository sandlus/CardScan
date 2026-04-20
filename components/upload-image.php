<?php

header("Content-Type: application/json");

$targetDir = "../uploads/images/";

if (!file_exists($targetDir)) {
    mkdir($targetDir, 0777, true);
}

if (!isset($_FILES['image'])) {
    echo json_encode([
        "status" => false,
        "message" => "No image received"
    ]);
    exit;
}

$file = $_FILES['image'];

$extension = pathinfo($file["name"], PATHINFO_EXTENSION);

// 👉 unique filename
$filename = time() . "_front_" . uniqid() . "." . $extension;

$targetFile = $targetDir . $filename;

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
        "message" => "Failed to upload"
    ]);
}