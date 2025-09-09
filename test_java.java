public class TestClass {
    public static void main(String[] args) {
        String userInput = args[0];
        String query = "SELECT * FROM users WHERE name = '" + userInput + "'";
        System.out.println(query);
        
        // This is a potential SQL injection vulnerability
        executeQuery(query);
    }
    
    private static void executeQuery(String sql) {
        // Database execution logic here
        System.out.println("Executing: " + sql);
    }
}