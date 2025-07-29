from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from ..core.dependencies import get_db, get_current_user
from ..models import User
from ..schemas.review import (
    ReviewCreate, 
    ReviewUpdate, 
    ReviewResponse, 
    ReviewListResponse,
    ReviewVoteCreate,
    ReviewVoteResponse
)
from ..services.review_service import ReviewService
from ..exceptions import NotFoundException, ConflictException, BadRequestException


router = APIRouter()


async def get_review_service(db: AsyncSession = Depends(get_db)) -> ReviewService:
    """Dependency function that provides an instance of ReviewService."""
    return ReviewService(db)


@router.post("/", response_model=ReviewResponse, status_code=201)
async def create_review(
    review_data: ReviewCreate,
    current_user: User = Depends(get_current_user),
    service: ReviewService = Depends(get_review_service)
):
    """
    **Create New Review**
    
    Create a new review for a product. Users can only review products once.
    
    **Request Body:**
    - **product_id**: ID of the product to review (required)
    - **rating**: Rating from 1-5 stars (required)
    - **title**: Review title (optional)
    - **comment**: Review comment/description (optional)
    
    **Features:**
    - Automatic verified purchase detection
    - Prevents duplicate reviews from same user
    - Validates rating is between 1-5
    """
    try:
        review = await service.create_review(current_user.id, review_data)
        return review
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ConflictException as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/product/{product_id}", response_model=ReviewListResponse)
async def get_product_reviews(
    product_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=50),
    sort_by: str = Query("created_at", regex="^(created_at|rating|helpful_votes)$"),
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
    service: ReviewService = Depends(get_review_service)
):
    """
    **Get Product Reviews**
    
    Retrieve all reviews for a specific product with pagination and sorting.
    
    **Path Parameters:**
    - **product_id**: ID of the product
    
    **Query Parameters:**
    - **skip**: Number of reviews to skip (default: 0)
    - **limit**: Maximum reviews to return (default: 10, max: 50)
    - **sort_by**: Sort field - created_at, rating, or helpful_votes (default: created_at)
    - **sort_order**: Sort direction - asc or desc (default: desc)
    
    **Returns:**
    - Paginated list of reviews
    - Review statistics (total, average rating, rating breakdown)
    """
    try:
        reviews, total_count, average_rating, rating_breakdown = await service.get_product_reviews(
            product_id, skip, limit, sort_by, sort_order
        )
        
        return {
            "items": reviews,
            "total": total_count,
            "page": skip // limit + 1 if limit > 0 else 1,
            "size": limit,
            "pages": (total_count + limit - 1) // limit if limit > 0 else 1,
            "average_rating": round(average_rating, 2),
            "rating_breakdown": rating_breakdown
        }
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/my-reviews", response_model=List[ReviewResponse])
async def get_my_reviews(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    service: ReviewService = Depends(get_review_service)
):
    """
    **Get My Reviews**
    
    Retrieve all reviews written by the current user.
    
    **Query Parameters:**
    - **skip**: Number of reviews to skip (default: 0)
    - **limit**: Maximum reviews to return (default: 10, max: 50)
    """
    try:
        reviews, total_count = await service.get_user_reviews(current_user.id, skip, limit)
        return reviews
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{review_id}", response_model=ReviewResponse)
async def update_review(
    review_id: int,
    review_data: ReviewUpdate,
    current_user: User = Depends(get_current_user),
    service: ReviewService = Depends(get_review_service)
):
    """
    **Update Review**
    
    Update an existing review. Users can only update their own reviews.
    
    **Path Parameters:**
    - **review_id**: ID of the review to update
    
    **Request Body:**
    - **rating**: New rating (optional)
    - **title**: New title (optional)
    - **comment**: New comment (optional)
    """
    try:
        review = await service.update_review(review_id, current_user.id, review_data)
        return review
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except BadRequestException as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{review_id}", status_code=204)
async def delete_review(
    review_id: int,
    current_user: User = Depends(get_current_user),
    service: ReviewService = Depends(get_review_service)
):
    """
    **Delete Review**
    
    Delete a review. Users can only delete their own reviews.
    
    **Path Parameters:**
    - **review_id**: ID of the review to delete
    """
    try:
        await service.delete_review(review_id, current_user.id)
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except BadRequestException as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{review_id}/vote", response_model=ReviewVoteResponse, status_code=201)
async def vote_review(
    review_id: int,
    vote_data: ReviewVoteCreate,
    current_user: User = Depends(get_current_user),
    service: ReviewService = Depends(get_review_service)
):
    """
    **Vote on Review**
    
    Vote whether a review is helpful or not helpful.
    
    **Path Parameters:**
    - **review_id**: ID of the review to vote on
    
    **Request Body:**
    - **is_helpful**: True if helpful, False if not helpful
    
    **Features:**
    - Users can change their vote
    - Automatically updates helpful vote count on review
    """
    try:
        vote = await service.vote_review(review_id, current_user.id, vote_data)
        return vote
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
