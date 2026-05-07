# Receipts

Receipts are provenance records for resolved semantic pointers.

Each receipt records:

- pointer
- type signature
- target language
- selected implementation string
- selected implementation hash
- catalog hash
- catalog ID
- catalog version
- artifact repo
- artifact revision
- resolver version
- resolution timestamp
- receipt ID

Receipts answer the audit question: "What did this compact pointer mean at resolution time?"

They do not prove that downstream execution happened, nor do they approve execution.
