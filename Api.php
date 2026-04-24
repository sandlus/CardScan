<?php
defined('BASEPATH') OR exit('No direct script access allowed');

class Api extends CI_Controller
{
    public function __construct()
    {
        parent::__construct();
        header("Content-Type: application/json");
    }

    public function get_branding()
    {
        // ✅ Get current domain dynamically
        $protocol = (!empty($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== 'off') ? "https://" : "http://";
        $domain = $protocol . $_SERVER['HTTP_HOST'] . "/";

        // ✅ Logo path
        $logoPath = FCPATH . "uploads/logo.png";
        $logoUrl  = $domain . "uploads/logo.png";

        // ✅ Check if file exists
        $logoFinal = file_exists($logoPath) ? $logoUrl : "";

        $response = [
            "status" => true,
            "company_name" => "Scanner", // you can customize per tenant if needed
            "logo" => $logoFinal,
            "primary_color" => "#0A74DA",
            "back_url" => $domain . "clogin",
            "favicon" => $logoFinal,

            // 🔍 DEBUG (remove later)
            "debug_domain" => $domain,
            "debug_logo_exists" => file_exists($logoPath),
            "debug_logo_path" => $logoPath
        ];

        echo json_encode($response);
    }
}