# Kode for å dekode og plotte bilde fra IR-kamera

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import re
import os

# Configuration
rel_path = r'IR-sensor\IR_output.txt'
IMAGE_WIDTH = 80  # Width of thermal image
IMAGE_HEIGHT = 60  # Height of thermal image


def parse_ir_data(file_path):
    """
    Parse IR sensor data from file.
    
    Args:
        file_path: Path to the IR output file
        
    Returns:
        List of tuples containing (frame_number, temperature_data)
    """
    frames = []
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Split by frame
    frame_blocks = re.split(r'Frame (\d+):', content)
    
    # Process each frame (skip first empty element)
    for i in range(1, len(frame_blocks), 2):
        frame_number = int(frame_blocks[i])
        frame_data = frame_blocks[i + 1].strip()
        
        if not frame_data:
            continue
            
        # Parse hex values
        hex_values = [val.strip() for val in frame_data.split(',') if val.strip()]
        
        # Convert hex to decimal
        decimal_values = []
        for hex_val in hex_values:
            try:
                decimal_values.append(int(hex_val, 16))
            except ValueError:
                continue
        
        # Extract temperature data (pairs of values: temp,marker)
        # Look for the pattern where every other value is 0x72, 0x73, 0x74, 0x75, 0x76
        # These appear to be temperature markers
        temperature_data = []
        i = 0
        while i < len(decimal_values) - 1:
            value = decimal_values[i]
            marker = decimal_values[i + 1]
            
            # Check if this looks like temperature data
            # Markers in range 0x72-0x76 (114-118) indicate valid temperature readings
            if 0x72 <= marker <= 0x76:
                # Temperature appears to be in the first byte
                # Scale it appropriately (adjust scaling as needed)
                temperature_data.append(value)
                i += 2
            elif marker == 0xFF:
                # End of valid data
                break
            else:
                i += 1
        
        if temperature_data:
            frames.append((frame_number, temperature_data))
    
    return frames


def reshape_to_image(data, width, height):
    """
    Reshape 1D temperature data to 2D image array.
    
    Args:
        data: 1D array of temperature values
        width: Image width
        height: Image height
        
    Returns:
        2D numpy array of shape (height, width)
    """
    expected_size = width * height
    
    # Pad or truncate data to match expected size
    if len(data) < expected_size:
        data = data + [0] * (expected_size - len(data))
    elif len(data) > expected_size:
        data = data[:expected_size]
    
    # Reshape to 2D array
    image = np.array(data).reshape(height, width)
    
    return image


def plot_single_frame(frame_number, temperature_data, width, height, save_path=None):
    """
    Plot a single thermal image frame.
    
    Args:
        frame_number: Frame identifier
        temperature_data: 1D array of temperature values
        width: Image width
        height: Image height
        save_path: Optional path to save the image
    """
    # Reshape data
    image = reshape_to_image(temperature_data, width, height)
    
    # Create plot
    plt.figure(figsize=(10, 8))
    
    # Plot heatmap
    im = plt.imshow(image, cmap='hot', interpolation='bilinear', aspect='auto')
    plt.colorbar(im, label='Temperature Value')
    plt.title(f'IR Thermal Image - Frame {frame_number}')
    plt.xlabel('X Position')
    plt.ylabel('Y Position')
    
    # Add value annotations
    for i in range(height):
        for j in range(width):
            text = plt.text(j, i, f'{image[i, j]:.0f}',
                          ha="center", va="center", color="white", fontsize=8)
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=150)
        print(f"Saved frame {frame_number} to {save_path}")
    
    plt.show()


def plot_all_frames(frames, width, height, save_dir=None):
    """
    Plot all frames in a grid layout.
    
    Args:
        frames: List of (frame_number, temperature_data) tuples
        width: Image width
        height: Image height
        save_dir: Optional directory to save individual images
    """
    if not frames:
        print("No frames to plot!")
        return
    
    # Determine grid layout
    n_frames = len(frames)
    cols = min(4, n_frames)
    rows = (n_frames + cols - 1) // cols
    
    # Create figure
    fig, axes = plt.subplots(rows, cols, figsize=(5*cols, 4*rows))
    fig.suptitle('IR Thermal Images - All Frames', fontsize=16)
    
    # Flatten axes array for easier iteration
    if n_frames == 1:
        axes = [axes]
    else:
        axes = axes.flatten() if n_frames > 1 else [axes]
    
    # Plot each frame
    for idx, (frame_number, temperature_data) in enumerate(frames):
        if idx >= len(axes):
            break
            
        ax = axes[idx]
        image = reshape_to_image(temperature_data, width, height)
        
        im = ax.imshow(image, cmap='hot', interpolation='bilinear', aspect='auto')
        ax.set_title(f'Frame {frame_number}')
        ax.set_xlabel('X Position')
        ax.set_ylabel('Y Position')
        plt.colorbar(im, ax=ax, label='Temp')
        
        # Save individual frame if requested
        if save_dir:
            os.makedirs(save_dir, exist_ok=True)
            frame_path = os.path.join(save_dir, f'frame_{frame_number}.png')
            single_fig, single_ax = plt.subplots(figsize=(8, 6))
            single_im = single_ax.imshow(image, cmap='hot', interpolation='bilinear')
            plt.colorbar(single_im, ax=single_ax, label='Temperature Value')
            single_ax.set_title(f'Frame {frame_number}')
            single_fig.savefig(frame_path, dpi=150, bbox_inches='tight')
            plt.close(single_fig)
    
    # Hide unused subplots
    for idx in range(n_frames, len(axes)):
        axes[idx].axis('off')
    
    plt.tight_layout()
    plt.show()


def create_animation(frames, width, height, output_file='ir_animation.gif', interval=500):
    """
    Create an animated GIF from all frames.
    
    Args:
        frames: List of (frame_number, temperature_data) tuples
        width: Image width
        height: Image height
        output_file: Output file name
        interval: Delay between frames in milliseconds
    """
    if not frames:
        print("No frames to animate!")
        return
    
    # Prepare images
    images = []
    frame_numbers = []
    for frame_number, temperature_data in frames:
        image = reshape_to_image(temperature_data, width, height)
        images.append(image)
        frame_numbers.append(frame_number)
    
    # Find global min/max for consistent color scale
    all_data = np.concatenate([img.flatten() for img in images])
    vmin, vmax = all_data.min(), all_data.max()
    
    # Create figure
    fig, ax = plt.subplots(figsize=(10, 8))
    
    # Initialize with first frame
    im = ax.imshow(images[0], cmap='hot', interpolation='bilinear', 
                   vmin=vmin, vmax=vmax, aspect='auto')
    plt.colorbar(im, ax=ax, label='Temperature Value')
    title = ax.set_title(f'Frame {frame_numbers[0]}')
    ax.set_xlabel('X Position')
    ax.set_ylabel('Y Position')
    
    def update(frame_idx):
        """Update function for animation."""
        im.set_data(images[frame_idx])
        title.set_text(f'Frame {frame_numbers[frame_idx]}')
        return [im, title]
    
    # Create animation
    anim = FuncAnimation(fig, update, frames=len(images), 
                        interval=interval, blit=True, repeat=True)
    
    # Save animation
    try:
        anim.save(output_file, writer='pillow', fps=1000/interval)
        print(f"Animation saved to {output_file}")
    except Exception as e:
        print(f"Could not save animation: {e}")
        print("Displaying animation instead...")
    
    plt.show()


def main():
    """Main function to process and visualize IR data."""
    
    # Get absolute path
    script_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(script_dir, 'IR_output.txt')
    
    print(f"Reading IR data from: {file_path}")
    
    # Check if file exists
    if not os.path.exists(file_path):
        print(f"Error: File not found at {file_path}")
        return
    
    # Parse data
    print("Parsing IR data...")
    frames = parse_ir_data(file_path)
    
    print(f"Found {len(frames)} frames with valid temperature data")
    
    if not frames:
        print("No valid frames found!")
        return
    
    # Display frame information
    for i, (frame_num, data) in enumerate(frames[:5]):  # Show first 5
        print(f"Frame {frame_num}: {len(data)} temperature readings")
    
    # Plot first frame with details
    if frames:
        print("\nPlotting first frame with details...")
        plot_single_frame(frames[0][0], frames[0][1], IMAGE_WIDTH, IMAGE_HEIGHT)
    
    # Plot all frames in grid
    if len(frames) > 1:
        print("\nPlotting all frames...")
        plot_all_frames(frames, IMAGE_WIDTH, IMAGE_HEIGHT)
        
        # Create animation
        print("\nCreating animation...")
        create_animation(frames, IMAGE_WIDTH, IMAGE_HEIGHT)
    
    print("\nDone!")


if __name__ == "__main__":
    main()

