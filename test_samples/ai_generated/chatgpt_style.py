# AI-Generated Code Example with Typical Patterns

def calculate_sum(numbers):
    """
    This function calculates the sum of an array of numbers.
    
    Args:
        numbers (list): A list of numbers to sum
        
    Returns:
        int: The sum of all numbers in the list
    """
    # Initialize sum to zero
    total = 0
    
    # Iterate through each number in the array
    for i in range(len(numbers)):
        # Add the current number to the total
        total += numbers[i]
    
    # Return the calculated sum
    return total

def process_data(data):
    """
    This function processes the input data and returns the result.
    
    Args:
        data (list): The input data to process
        
    Returns:
        list: The processed data
    """
    # Initialize result list
    result = []
    
    # Check if data is not empty
    if data:
        # Process each item in the data
        for item in data:
            # Check if item is valid
            if item is not None:
                # Process the item
                processed_item = item * 2
                # Add to result
                result.append(processed_item)
    
    # Return the result
    return result

def validate_input(input_value):
    """
    This function validates the input value.
    
    Args:
        input_value: The value to validate
        
    Returns:
        bool: True if valid, False otherwise
    """
    # Check if input is not None
    if input_value is not None:
        # Check if input is not empty
        if len(str(input_value)) > 0:
            # Input is valid
            return True
        else:
            # Input is empty
            return False
    else:
        # Input is None
        return False

class DataManager:
    """
    This class manages data operations.
    """
    
    def __init__(self):
        """
        Initialize the DataManager.
        """
        # Initialize data storage
        self.data = []
        # Initialize counter
        self.count = 0
    
    def add_data(self, item):
        """
        Add an item to the data storage.
        
        Args:
            item: The item to add
        """
        # Add item to data
        self.data.append(item)
        # Increment counter
        self.count += 1
    
    def get_data(self):
        """
        Get all data from storage.
        
        Returns:
            list: All stored data
        """
        # Return the data
        return self.data
    
    def clear_data(self):
        """
        Clear all data from storage.
        """
        # Clear the data list
        self.data = []
        # Reset counter
        self.count = 0

# Example usage
if __name__ == "__main__":
    # Create a list of numbers
    numbers = [1, 2, 3, 4, 5]
    
    # Calculate the sum
    result = calculate_sum(numbers)
    
    # Print the result
    print(f"The sum is: {result}")
    
    # Create data manager instance
    manager = DataManager()
    
    # Add some data
    manager.add_data("item1")
    manager.add_data("item2")
    
    # Get the data
    stored_data = manager.get_data()
    
    # Print the stored data
    print(f"Stored data: {stored_data}")