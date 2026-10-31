import fitz

def create_sample_pdf(output_path="sample_speechify.pdf"):
    doc = fitz.open()
    
    # Page 1
    page1 = doc.new_page(width=595, height=842) # A4 size
    
    # Title
    page1.insert_text((50, 80), "SPEECHIFY LOCAL: NEURAL PDF READER", fontsize=20, fontname="helv", color=(0.1, 0.2, 0.4))
    page1.insert_text((50, 105), "Autonomous On-Device Document Synthesis & Vision Alignment", fontsize=11, fontname="helv", color=(0.4, 0.4, 0.4))
    
    # Horizontal line
    page1.draw_line((50, 120), (545, 120), color=(0.8, 0.8, 0.8), width=1)
    
    # Abstract Box
    rect_abs = fitz.Rect(50, 140, 545, 230)
    page1.draw_rect(rect_abs, color=(0.2, 0.4, 0.8), fill=(0.95, 0.97, 1.0), width=0.5)
    page1.insert_text((65, 160), "ABSTRACT", fontsize=11, fontname="helv", color=(0.1, 0.3, 0.7))
    abstract_text = (
        "This system demonstrates real-time neural speech synthesis synchronized directly with "
        "original document layout geometry. By aligning acoustic token generation with visual "
        "bounding coordinates, users experience seamless audio-visual reading without altering the "
        "native formatting of complex documents, charts, or academic publications."
    )
    page1.insert_textbox(fitz.Rect(65, 170, 530, 225), abstract_text, fontsize=9.5, fontname="times-roman", lineheight=1.4)
    
    # Two column section
    col1 = fitz.Rect(50, 250, 285, 750)
    col2 = fitz.Rect(310, 250, 545, 750)
    
    col1_text = (
        "1. INTRODUCTION\n\n"
        "Reading long-form documentation often requires high cognitive effort. "
        "Traditional text-to-speech engines strip away original typography, losing critical spatial context. "
        "In contrast, Speechify Local preserves the exact visual presentation of the original PDF.\n\n"
        "2. HARDWARE ACCELERATION\n\n"
        "Modern deep learning workflows benefit from local tensor parallelism. "
        "The Kokoro-82M model executes with sub-second latency on consumer graphics hardware. "
        "Audio waveforms are computed using continuous diffusion models and spectrogram decoders."
    )
    page1.insert_textbox(col1, col1_text, fontsize=10, fontname="times-roman", lineheight=1.5)
    
    col2_text = (
        "3. ZERO-LATENCY PRELOADING\n\n"
        "To achieve continuous speech without perceptible pauses, the playback engine maintains a predictive pipeline. "
        "While sentence N is actively spoken, sentences N+1 and N+2 are rendered in system memory. "
        "This completely eliminates buffering delays during long reading sessions.\n\n"
        "4. BOUNDING BOX SYNCHRONIZATION\n\n"
        "Each sentence is mapped to its exact coordinate rectangle on the rendered page canvas. "
        "When playback advances, the corresponding region illuminates with a soft amber highlight. "
        "Readers can also click any paragraph directly to jump audio to that position."
    )
    page1.insert_textbox(col2, col2_text, fontsize=10, fontname="times-roman", lineheight=1.5)
    
    # Footer
    page1.insert_text((270, 810), "Page 1 of 2", fontsize=9, fontname="helv", color=(0.5, 0.5, 0.5))

    # Page 2
    page2 = doc.new_page(width=595, height=842)
    page2.insert_text((50, 80), "SYSTEM ARCHITECTURE & BENCHMARKS", fontsize=16, fontname="helv", color=(0.1, 0.2, 0.4))
    page2.draw_line((50, 95), (545, 95), color=(0.8, 0.8, 0.8), width=1)
    
    p2_body = (
        "5. PERFORMANCE METRICS\n\n"
        "Benchmarks on NVIDIA RTX series GPUs demonstrate an inference speedup of over 15x real time. "
        "This allows high-fidelity 24kHz audio synthesis with negligible power consumption. "
        "Memory consumption remains under 400 megabytes during active reading.\n\n"
        "6. PRIVACY & DATA SOVEREIGNTY\n\n"
        "Unlike commercial cloud subscriptions, Speechify Local processes all files within your local environment. "
        "Sensitive business contracts, proprietary research, and private eBooks never leave your computer. "
        "Everything runs offline, guaranteeing total confidentiality."
    )
    page2.insert_textbox(fitz.Rect(50, 115, 545, 450), p2_body, fontsize=10.5, fontname="times-roman", lineheight=1.6)
    
    # Diagram / table box
    table_rect = fitz.Rect(50, 480, 545, 680)
    page2.draw_rect(table_rect, color=(0.3, 0.3, 0.3), fill=(0.98, 0.98, 0.98), width=1)
    page2.insert_text((70, 510), "Model Configuration Summary", fontsize=12, fontname="helv", color=(0.1, 0.1, 0.1))
    
    table_data = (
        "• Primary Neural Backbone: Kokoro-82M Open-Weights Architecture\n\n"
        "• Sampling Frequency: 24,000 Hz Mono Waveform Audio\n\n"
        "• Acceleration Engine: PyTorch with CUDA & TensorRT compatibility\n\n"
        "• Document Geometry Parser: PyMuPDF with Multi-Line Rect Extraction\n\n"
        "• Client Protocol: HTML5 Audio with MediaSession & PWA integration"
    )
    page2.insert_textbox(fitz.Rect(70, 530, 520, 660), table_data, fontsize=10, fontname="helv", lineheight=1.5)
    page2.insert_text((270, 810), "Page 2 of 2", fontsize=9, fontname="helv", color=(0.5, 0.5, 0.5))

    doc.save(output_path)
    doc.close()
    print(f"Sample PDF created successfully at {output_path}")

if __name__ == "__main__":
    create_sample_pdf()
