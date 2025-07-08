from pydantic import BaseModel


class FlashSalesSchema(BaseModel):
    name: str
    description: str
    start_time: str
    end_time: str
    discount_percentage: float

    class Config:
        orm_mode = True


class CreateFlashSaleSchema(FlashSalesSchema):
    pass


class FlashSalesSchemaResponse(FlashSalesSchema):
    id: int
