from sqlalchemy import func, select, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from typing import List, Optional, Tuple

from ..models import Review, ReviewVote, Product, User, OrderItem
from ..schemas.review import ReviewCreate, ReviewUpdate, ReviewVoteCreate
from ..exceptions import NotFoundException, ConflictException, BadRequestException


class ReviewService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_review(self, user_id: int, review_data: ReviewCreate) -> Review:
        """Create a new review for a product"""
        
        # Check if product exists
        product_query = select(Product).where(Product.id == review_data.product_id)
        product_result = await self.db.execute(product_query)
        product = product_result.scalar_one_or_none()
        
        if not product:
            raise NotFoundException("Product not found")
        
        # Check if user already reviewed this product
        existing_review_query = select(Review).where(
            and_(Review.user_id == user_id, Review.product_id == review_data.product_id)
        )
        existing_review_result = await self.db.execute(existing_review_query)
        existing_review = existing_review_result.scalar_one_or_none()
        
        if existing_review:
            raise ConflictException("You have already reviewed this product")
        
        # Check if user purchased this product (verified purchase)
        purchase_query = select(OrderItem).join(OrderItem.order).where(
            and_(
                OrderItem.product_id == review_data.product_id,
                OrderItem.order.has(customer_id=user_id)
            )
        )
        purchase_result = await self.db.execute(purchase_query)
        is_verified_purchase = purchase_result.scalar_one_or_none() is not None
        
        # Create review
        review = Review(
            user_id=user_id,
            product_id=review_data.product_id,
            rating=review_data.rating,
            title=review_data.title,
            comment=review_data.comment,
            is_verified_purchase=is_verified_purchase
        )
        
        self.db.add(review)
        await self.db.commit()
        await self.db.refresh(review)
        
        return review

    async def get_product_reviews(
        self, 
        product_id: int, 
        skip: int = 0, 
        limit: int = 10,
        sort_by: str = "created_at",
        sort_order: str = "desc"
    ) -> Tuple[List[Review], int, float, dict]:
        """Get reviews for a product with pagination and sorting"""
        
        # Check if product exists
        product_query = select(Product).where(Product.id == product_id)
        product_result = await self.db.execute(product_query)
        product = product_result.scalar_one_or_none()
        
        if not product:
            raise NotFoundException("Product not found")
        
        # Build base query
        base_query = select(Review).where(
            and_(Review.product_id == product_id, Review.is_approved == True)
        ).options(selectinload(Review.user))
        
        # Add sorting
        if sort_by == "rating":
            order_field = Review.rating
        elif sort_by == "helpful_votes":
            order_field = Review.helpful_votes
        else:  # default to created_at
            order_field = Review.created_at
            
        if sort_order.lower() == "asc":
            base_query = base_query.order_by(order_field.asc())
        else:
            base_query = base_query.order_by(order_field.desc())
        
        # Get total count
        count_query = select(func.count()).select_from(Review).where(
            and_(Review.product_id == product_id, Review.is_approved == True)
        )
        count_result = await self.db.execute(count_query)
        total_count = count_result.scalar()
        
        # Get paginated reviews
        paginated_query = base_query.offset(skip).limit(limit)
        reviews_result = await self.db.execute(paginated_query)
        reviews = reviews_result.scalars().all()
        
        # Calculate average rating
        avg_query = select(func.avg(Review.rating)).where(
            and_(Review.product_id == product_id, Review.is_approved == True)
        )
        avg_result = await self.db.execute(avg_query)
        average_rating = avg_result.scalar() or 0.0
        
        # Get rating breakdown
        rating_breakdown = {}
        for rating in range(1, 6):
            rating_query = select(func.count()).select_from(Review).where(
                and_(
                    Review.product_id == product_id,
                    Review.is_approved == True,
                    Review.rating >= rating,
                    Review.rating < rating + 1
                )
            )
            rating_result = await self.db.execute(rating_query)
            rating_breakdown[rating] = rating_result.scalar()
        
        return reviews, total_count, average_rating, rating_breakdown

    async def get_user_reviews(
        self, 
        user_id: int, 
        skip: int = 0, 
        limit: int = 10
    ) -> Tuple[List[Review], int]:
        """Get all reviews by a user"""
        
        # Build query
        query = select(Review).where(Review.user_id == user_id).options(
            selectinload(Review.product)
        ).order_by(desc(Review.created_at))
        
        # Get total count
        count_query = select(func.count()).select_from(Review).where(Review.user_id == user_id)
        count_result = await self.db.execute(count_query)
        total_count = count_result.scalar()
        
        # Get paginated reviews
        paginated_query = query.offset(skip).limit(limit)
        reviews_result = await self.db.execute(paginated_query)
        reviews = reviews_result.scalars().all()
        
        return reviews, total_count

    async def update_review(self, review_id: int, user_id: int, review_data: ReviewUpdate) -> Review:
        """Update a review (only by the review author)"""
        
        # Get review
        review_query = select(Review).where(Review.id == review_id)
        review_result = await self.db.execute(review_query)
        review = review_result.scalar_one_or_none()
        
        if not review:
            raise NotFoundException("Review not found")
        
        if review.user_id != user_id:
            raise BadRequestException("You can only update your own reviews")
        
        # Update fields
        if review_data.rating is not None:
            review.rating = review_data.rating
        if review_data.title is not None:
            review.title = review_data.title
        if review_data.comment is not None:
            review.comment = review_data.comment
        
        await self.db.commit()
        await self.db.refresh(review)
        
        return review

    async def delete_review(self, review_id: int, user_id: int) -> None:
        """Delete a review (only by the review author)"""
        
        # Get review
        review_query = select(Review).where(Review.id == review_id)
        review_result = await self.db.execute(review_query)
        review = review_result.scalar_one_or_none()
        
        if not review:
            raise NotFoundException("Review not found")
        
        if review.user_id != user_id:
            raise BadRequestException("You can only delete your own reviews")
        
        await self.db.delete(review)
        await self.db.commit()

    async def vote_review(self, review_id: int, user_id: int, vote_data: ReviewVoteCreate) -> ReviewVote:
        """Vote on a review as helpful or not helpful"""
        
        # Check if review exists
        review_query = select(Review).where(Review.id == review_id)
        review_result = await self.db.execute(review_query)
        review = review_result.scalar_one_or_none()
        
        if not review:
            raise NotFoundException("Review not found")
        
        # Check if user already voted on this review
        existing_vote_query = select(ReviewVote).where(
            and_(ReviewVote.review_id == review_id, ReviewVote.user_id == user_id)
        )
        existing_vote_result = await self.db.execute(existing_vote_query)
        existing_vote = existing_vote_result.scalar_one_or_none()
        
        if existing_vote:
            # Update existing vote
            existing_vote.is_helpful = vote_data.is_helpful
            vote = existing_vote
        else:
            # Create new vote
            vote = ReviewVote(
                review_id=review_id,
                user_id=user_id,
                is_helpful=vote_data.is_helpful
            )
            self.db.add(vote)
        
        # Update helpful votes count on review
        helpful_votes_query = select(func.count()).select_from(ReviewVote).where(
            and_(ReviewVote.review_id == review_id, ReviewVote.is_helpful == True)
        )
        helpful_votes_result = await self.db.execute(helpful_votes_query)
        review.helpful_votes = helpful_votes_result.scalar()
        
        await self.db.commit()
        await self.db.refresh(vote)
        
        return vote
