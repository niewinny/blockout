
void main()
{
    // Compute the distance along the line, incorporating cumulative length
    float alongLineDistance =  v_Length;
    
    float position = mod(alongLineDistance, lineSize * 2.0);
    if (position > lineSize) discard;

    FragColor = v_Color;
}
