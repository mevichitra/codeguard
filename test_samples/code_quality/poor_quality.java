// Poor Code Quality Examples

public class DataProcessor {
    
    // ISSUE: Method too long, deeply nested, poor readability
    public void processUserData(String userData, String userType, boolean isActive, int priority) {
        if (userData != null) {
            if (userData.length() > 0) {
                if (!userData.isEmpty()) {
                    if (userData.trim().length() > 0) {
                        if (userType != null) {
                            if (userType.equals("premium")) {
                                if (isActive) {
                                    if (priority > 5) {
                                        if (priority < 10) {
                                            // ISSUE: Deep nesting (8 levels)
                                            String[] parts = userData.split(",");
                                            for (int i = 0; i < parts.length; i++) {
                                                if (parts[i] != null) {
                                                    if (parts[i].length() > 0) {
                                                        if (!parts[i].trim().isEmpty()) {
                                                            // Finally process the data
                                                            System.out.println("Processing: " + parts[i]);
                                                        }
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    
    // ISSUE: Code duplication - almost identical to above method
    public void processAdminData(String adminData, String adminType, boolean isActive, int priority) {
        if (adminData != null) {
            if (adminData.length() > 0) {
                if (!adminData.isEmpty()) {
                    if (adminData.trim().length() > 0) {
                        if (adminType != null) {
                            if (adminType.equals("super")) {
                                if (isActive) {
                                    if (priority > 5) {
                                        if (priority < 10) {
                                            String[] parts = adminData.split(",");
                                            for (int i = 0; i < parts.length; i++) {
                                                if (parts[i] != null) {
                                                    if (parts[i].length() > 0) {
                                                        if (!parts[i].trim().isEmpty()) {
                                                            System.out.println("Admin Processing: " + parts[i]);
                                                        }
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    
    // ISSUE: Magic numbers, unclear variable names, no comments
    public int calc(int x, int y, int z) {
        int a = x * 42;
        int b = y + 1337;
        int c = z / 7;
        
        if (a > 1000) {
            b = b * 2;
        }
        
        return a + b - c + 999;
    }
    
    // ISSUE: Long parameter list, unclear method purpose
    public void doSomething(String s1, String s2, String s3, int i1, int i2, int i3, 
                           boolean b1, boolean b2, boolean b3, double d1, double d2) {
        // ISSUE: Empty catch block, swallowing exceptions
        try {
            // Some risky operation
            int result = Integer.parseInt(s1) / Integer.parseInt(s2);
        } catch (Exception e) {
            // Silently ignore all exceptions
        }
    }
    
    // ISSUE: God class - too many responsibilities
    public void handleEverything() {
        // Database operations
        connectToDatabase();
        
        // File operations
        readFromFile();
        
        // Network operations
        sendHttpRequest();
        
        // UI operations
        updateUserInterface();
        
        // Business logic
        calculateBusinessMetrics();
        
        // Logging
        writeToLog();
    }
    
    // ISSUE: Methods with unclear names and no documentation
    private void connectToDatabase() { /* implementation */ }
    private void readFromFile() { /* implementation */ }
    private void sendHttpRequest() { /* implementation */ }
    private void updateUserInterface() { /* implementation */ }
    private void calculateBusinessMetrics() { /* implementation */ }
    private void writeToLog() { /* implementation */ }
    
    // ISSUE: Inconsistent naming conventions
    public String user_name;
    public String UserEmail;
    public String USERID;
    public String phoneNumber;
}