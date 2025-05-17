import matplotlib.pyplot as plt
from PIL import Image
import io
from model import graph


def show_graph():
    try:
        # Get the graph as PNG bytes
        png_bytes = graph.get_graph().draw_mermaid_png()

        # Convert bytes to PIL Image
        img = Image.open(io.BytesIO(png_bytes))

        # Create a matplotlib figure and display the image
        plt.figure(figsize=(8, 8))
        plt.imshow(img)
        plt.axis("off")  # Hide axes
        plt.show()
    except Exception as e:
        print(f"Error displaying graph: {e}")


if __name__ == "__main__":
    show_graph()
