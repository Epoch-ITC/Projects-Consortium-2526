from ultralytics.models.sam import SAM3SemanticPredictor

# load model
predictor = SAM3SemanticPredictor(model="sam3.pt")

# set image
predictor.set_image("/home/adishesh/Real-Time-Bird-Species-Detection/another-bird-dataset/test/images/mia-nelson-Zz1bn9a74Wc-unsplash_jpg.rf.2d234a7da0a76bbf771d2b36748ac25d.jpg")

# run prompt
results = predictor(text=["cat", "person"])

# view masks
for mask in results.masks:
    mask.show()
