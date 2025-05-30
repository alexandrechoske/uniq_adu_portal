from fpdf import FPDF

def create_sample_invoice_pdf():
    # Create instance of FPDF class
    pdf = FPDF()
    
    # Add a page
    pdf.add_page()
    
    # Set style and size of font
    pdf.set_font("Arial", "B", 16)
    
    # Set header
    pdf.cell(200, 10, txt="INVOICE", ln=True, align='C')
    pdf.ln(10)
    
    # Invoice details
    pdf.set_font("Arial", "", 12)
    pdf.cell(200, 8, txt="Invoice Number: INV-2023-001", ln=True)
    pdf.cell(200, 8, txt="Date: 15/03/2023", ln=True)
    pdf.ln(5)
    
    # Exporter info
    pdf.set_font("Arial", "B", 12)
    pdf.cell(200, 8, txt="Exporter:", ln=True)
    pdf.set_font("Arial", "", 12)
    pdf.cell(200, 8, txt="Shanghai Electronics Co., Ltd.", ln=True)
    pdf.cell(200, 8, txt="123 Export Street, Shanghai, China", ln=True)
    pdf.ln(5)
    
    # Importer info
    pdf.set_font("Arial", "B", 12)
    pdf.cell(200, 8, txt="Importer:", ln=True)
    pdf.set_font("Arial", "", 12)
    pdf.cell(200, 8, txt="Importadora Brasil Ltda.", ln=True)
    pdf.cell(200, 8, txt="456 Import Avenue, Santos, Brazil", ln=True)
    pdf.ln(10)
    
    # Table Header
    pdf.set_font("Arial", "B", 12)
    pdf.cell(10, 8, txt="No", border=1)
    pdf.cell(75, 8, txt="Description", border=1)
    pdf.cell(35, 8, txt="Quantity", border=1)
    pdf.cell(35, 8, txt="Unit Price", border=1)
    pdf.cell(35, 8, txt="Total", border=1, ln=True)
    
    # Table Data
    pdf.set_font("Arial", "", 12)
    
    # Row 1
    pdf.cell(10, 8, txt="1", border=1)
    pdf.cell(75, 8, txt="Smartphone Model X", border=1)
    pdf.cell(35, 8, txt="100 pcs", border=1)
    pdf.cell(35, 8, txt="USD 250.00", border=1)
    pdf.cell(35, 8, txt="USD 25,000.00", border=1, ln=True)
    
    # Row 2
    pdf.cell(10, 8, txt="2", border=1)
    pdf.cell(75, 8, txt="Tablet Model Y", border=1)
    pdf.cell(35, 8, txt="50 pcs", border=1)
    pdf.cell(35, 8, txt="USD 300.00", border=1)
    pdf.cell(35, 8, txt="USD 15,000.00", border=1, ln=True)
    
    # Row 3
    pdf.cell(10, 8, txt="3", border=1)
    pdf.cell(75, 8, txt="Laptop Model Z", border=1)
    pdf.cell(35, 8, txt="20 pcs", border=1)
    pdf.cell(35, 8, txt="USD 800.00", border=1)
    pdf.cell(35, 8, txt="USD 16,000.00", border=1, ln=True)
    
    # Summary
    pdf.ln(10)
    pdf.cell(120)
    pdf.cell(40, 8, txt="Subtotal:", border=0)
    pdf.cell(40, 8, txt="USD 56,000.00", border=0, ln=True)
    
    pdf.cell(120)
    pdf.cell(40, 8, txt="Freight:", border=0)
    pdf.cell(40, 8, txt="USD 2,500.00", border=0, ln=True)
    
    pdf.cell(120)
    pdf.cell(40, 8, txt="Insurance:", border=0)
    pdf.cell(40, 8, txt="USD 500.00", border=0, ln=True)
    
    pdf.set_font("Arial", "B", 12)
    pdf.cell(120)
    pdf.cell(40, 8, txt="Total Value:", border=0)
    pdf.cell(40, 8, txt="USD 59,000.00", border=0, ln=True)
    
    # Additional information
    pdf.ln(10)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(200, 8, txt="Terms and Conditions:", ln=True)
    pdf.set_font("Arial", "", 12)
    pdf.cell(200, 8, txt="Incoterm: FOB Shanghai", ln=True)
    pdf.cell(200, 8, txt="Country of Origin: China", ln=True)
    pdf.cell(200, 8, txt="Country of Acquisition: China", ln=True)
    pdf.cell(200, 8, txt="Payment Term: 30 days", ln=True)
      # Output PDF
    try:
        import os
        output_dir = os.path.join("static", "uploads", "conferencia")
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, "sample_invoice.pdf")
        pdf.output(output_path)
        print(f"Sample invoice PDF created at: {output_path}")
    except Exception as e:
        print(f"Error creating PDF: {str(e)}")

if __name__ == "__main__":
    create_sample_invoice_pdf()
