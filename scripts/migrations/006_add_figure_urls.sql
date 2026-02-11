-- Add figure_urls column to patents table
-- Stores array of image URLs from Google Patents

ALTER TABLE patents
ADD COLUMN IF NOT EXISTS figure_urls TEXT[];

-- Add comment for documentation
COMMENT ON COLUMN patents.figure_urls IS 'Array of patent figure/drawing URLs from Google Patents storage';
