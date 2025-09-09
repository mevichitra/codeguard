<?php
// Mixed Security Vulnerabilities Example

// VULNERABILITY: XSS - Unescaped user input
function displayUserComment($comment) {
    echo "<div class='comment'>" . $comment . "</div>";
}

// VULNERABILITY: SQL Injection
function getUserById($id) {
    $connection = mysqli_connect("localhost", "user", "password", "database");
    $query = "SELECT * FROM users WHERE id = " . $id;
    return mysqli_query($connection, $query);
}

// VULNERABILITY: Insecure direct object reference
function downloadFile($filename) {
    $filepath = "/uploads/" . $filename;
    // No access control or path validation
    if (file_exists($filepath)) {
        header('Content-Type: application/octet-stream');
        readfile($filepath);
    }
}

// VULNERABILITY: Weak session management
session_start();
if (!isset($_SESSION['csrf_token'])) {
    // VULNERABILITY: Predictable token generation
    $_SESSION['csrf_token'] = md5(time());
}

// VULNERABILITY: Information disclosure
function debugInfo() {
    if ($_GET['debug'] == '1') {
        phpinfo();
        echo "Database password: mySecretPassword123";
        echo "API Key: sk-1234567890abcdef";
    }
}

// VULNERABILITY: Command injection
function pingHost($host) {
    $command = "ping -c 4 " . $host;
    return shell_exec($command);
}

// VULNERABILITY: Insecure file upload
function uploadFile() {
    $target_dir = "uploads/";
    $target_file = $target_dir . basename($_FILES["fileToUpload"]["name"]);
    
    // No file type validation
    if (move_uploaded_file($_FILES["fileToUpload"]["tmp_name"], $target_file)) {
        echo "File uploaded successfully.";
    }
}

// VULNERABILITY: Weak cryptography
function encryptPassword($password) {
    return md5($password); // Weak hashing algorithm
}

// VULNERABILITY: Insecure random number generation
function generateToken() {
    return rand(1000, 9999); // Predictable random numbers
}

// VULNERABILITY: Missing access control
function deleteUser($userId) {
    // No authentication or authorization check
    $connection = mysqli_connect("localhost", "user", "password", "database");
    $query = "DELETE FROM users WHERE id = " . $userId;
    mysqli_query($connection, $query);
}

// VULNERABILITY: Hardcoded credentials
class DatabaseConfig {
    const DB_HOST = "localhost";
    const DB_USER = "admin";
    const DB_PASS = "admin123"; // Hardcoded password
    const API_SECRET = "hardcoded_secret_key_2024";
}

// VULNERABILITY: Insecure cookie settings
function setUserCookie($username) {
    // No secure flag, no httponly flag
    setcookie("username", $username, time() + 3600, "/");
    setcookie("admin", "true", time() + 3600, "/");
}

// VULNERABILITY: LDAP injection
function authenticateUser($username, $password) {
    $ldapconn = ldap_connect("ldap://localhost");
    $filter = "(&(uid=" . $username . ")(password=" . $password . "))";
    return ldap_search($ldapconn, "dc=example,dc=com", $filter);
}

// VULNERABILITY: XML External Entity (XXE)
function parseXML($xmlString) {
    $dom = new DOMDocument();
    $dom->loadXML($xmlString, LIBXML_NOENT | LIBXML_DTDLOAD);
    return $dom;
}

// VULNERABILITY: Insecure deserialization
function processUserData($serializedData) {
    return unserialize($serializedData); // Dangerous deserialization
}

// Main application logic with vulnerabilities
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    // VULNERABILITY: No CSRF protection
    if (isset($_POST['comment'])) {
        displayUserComment($_POST['comment']);
    }
    
    if (isset($_POST['user_id'])) {
        $user = getUserById($_POST['user_id']);
    }
    
    if (isset($_POST['host'])) {
        $result = pingHost($_POST['host']);
    }
}

// VULNERABILITY: Sensitive information in error messages
try {
    $connection = mysqli_connect("localhost", "wronguser", "wrongpass", "database");
} catch (Exception $e) {
    echo "Database connection failed: " . $e->getMessage();
    echo "Connection string: localhost:3306 with user 'admin' and password 'secret123'";
}

?>