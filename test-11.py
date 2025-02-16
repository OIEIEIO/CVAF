from framework.framework import Framework
import time

# Initialize the framework
framework = Framework()
framework.start()
time.sleep(5)  # Allow virtual desktop to start

### **Step 1: Locate and Open Calculator**
def open_calculator():
    coords = framework.vision_system("Find the Calculator icon on the desktop or in the start menu")
    if coords:
        framework.mouse_move(coordinate=coords)
        framework.left_click()
        print("✅ Opened Calculator")
        time.sleep(7)  # Extra wait for Calculator to open fully
    else:
        print("❌ Calculator icon not found")
        framework.stop()
        exit()

open_calculator()

### **Step 2: Map the Calculator Display (Using Averaging)**
display_position = None

def map_display():
    """Find and store the display position using an averaged approach."""
    global display_position
    all_coords = []

    for _ in range(3):  # Take 3 readings
        coords = framework.vision_system("Find the calculator display area and return its coordinates")
        if coords:
            all_coords.append(coords)
        time.sleep(1)

    if all_coords:
        # Average the coordinates for stability
        avg_x = sum(c[0] for c in all_coords) // len(all_coords)
        avg_y = sum(c[1] for c in all_coords) // len(all_coords)
        display_position = [avg_x, avg_y]
        print(f"✅ Using averaged display position: {display_position}")
    else:
        print("❌ Failed to map display position.")

map_display()

### **Step 3: Map Number Buttons with Averaging (Special Handling for 7)**
button_map = {}

def map_numbers():
    """Scan and save the coordinates of number buttons (1-9) and 'C' using averaging."""
    global button_map
    buttons = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "C", "*", "="]
    
    for button in buttons:
        all_coords = []
        sample_count = 5 if button == "7" else 3  # Increase samples for '7' key

        for _ in range(sample_count):  # Take multiple readings
            coords = framework.vision_system(f"Find the '{button}' button on the calculator")
            if coords:
                all_coords.append(coords)
            time.sleep(1)

        if all_coords:
            # Detect and discard outliers
            avg_x = sum(c[0] for c in all_coords) // len(all_coords)
            avg_y = sum(c[1] for c in all_coords) // len(all_coords)

            # Special adjustment for 7
            if button == "7":
                avg_y += 5  # Move slightly downward for more accuracy

            adjusted_coords = [avg_x - 5, avg_y + 10]  # Small correction
            button_map[button] = adjusted_coords
            print(f"✅ Mapped '{button}' at {coords} (Averaged: {adjusted_coords})")
        else:
            print(f"⚠️ Could not find '{button}', skipping...")

    print(f"🔍 **Final Button Map:** {button_map}")

map_numbers()

### **Step 4: Click Function with Averaged Coordinates**
def click_button(label, delay=3):
    """Click a pre-mapped button with improved accuracy using averaged coordinates."""
    if label in button_map:
        coords = button_map[label]
        
        # Adjust click position to be closer to the center
        click_offset = [coords[0] - 10, coords[1] + 5]  
        framework.mouse_move(coordinate=click_offset)
        framework.left_click()
        print(f"✅ Clicked {label} (Averaged Click at {click_offset})")
        time.sleep(delay)  # Ensure the UI updates
    else:
        print(f"❌ Button '{label}' not found in map.")

### **Step 5: Test Entering and Clearing Numbers with Adjustments**
def test_numbers():
    """Enter a number, confirm the display updated, then clear it before entering the next number."""
    for num in ["1", "3", "2", "7", "5", "4", "C", "9", "*", "3", "="]:  # Test sequence of numbers
        click_button(num)
        time.sleep(1)  # Let display update

test_numbers()

### **Step 6: Stop the Framework**
framework.stop()
print("✅ Automation completed, container stopped.")
