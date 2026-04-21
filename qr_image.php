<?php
defined('BASEPATH') OR exit('No direct script access allowed');


class Card_list extends MY_user_Controller {

    function __construct() {
        parent::__construct();
        $this->load->model("card_model", "card");	
    }
public function save_qr() {

    $data = json_decode(file_get_contents("php://input"), true);

    if (empty($data['qr_image'])) {
        echo json_encode(["status" => false, "message" => "No image"]);
        return;
    }

    $imageData = base64_decode($data['qr_image']);

    $fileName = 'qr_' . time() . '.png';

    file_put_contents(FCPATH . 'uploads/images/' . $fileName, $imageData);

    // Save DB
    $this->db->insert('scan_card', [
        'name' => $data['name'],
        'phone' => $data['phone'],
        'qr_image' => $fileName
    ]);

    echo json_encode([
        "status" => true,
        "file" => $fileName
    ]);
}