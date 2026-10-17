c-----------------------------------------------------------------------
      program p7h_vcbar_oracle
c-----------------------------------------------------------------------
c
c --- CTEAS P7H FORTRAN ORACLE DRIVER -- hand written for this test
c     harness. This file is NOT vendor source and is never used by the
c     model; it drives the UNMODIFIED vendor units extracted by
c     reference/p7h_source_anchor.py: VCBAR, VCOUP and CTADJ.
c
c --- Input on stdin, list directed:
c     line 1: mode  1 = VCOUP matrix, 2 = VCBAR matrix
c     mode 1: icase icode zr zs sz hlid hlidmax
c     mode 2: icase mfact0 icode mctadj mtilt hlid ppcoef dgridi ht0 elbase
c                    zb1 ze1 szb1 szm1 sze1 zb2 ze2 szb2 sze2 tb1 te1 tb2 te2
c                    zfinal vsetl
c     Output: icase value
c-----------------------------------------------------------------------
      include 'params.puf'
      include 'flags.puf'
      include 'grid.puf'
      include 'puff.puf'
      include 'current.puf'
c
      integer mode,ios,icase,mfact0,icodein,mctadj_in,mtilt_in
      real zr,zs,sz,hlid,hlidmax,ppcoef,dgridi,ht0in,elbasein
      real zb1in,ze1in,szb1in,szm1in,sze1in,zb2in,ze2in,szb2in,sze2in
      real tb1in,te1in,tb2in,te2in,zfinalin,vsetlin
      real value
      logical lcalm
c
      lcalm=.FALSE.
      read(*,*,iostat=ios) mode
      if(ios.ne.0) stop 'P7H oracle: missing mode'
c
      if(mode.eq.1)then
 10      read(*,*,iostat=ios) icase,icode,zr,zs,sz,hlid,hlidmax
         if(ios.ne.0) goto 999
         value=vcoup(icode,zr,zs,sz,hlid,hlidmax)
         write(*,'(i8,1x,es20.12)') icase,value
         goto 10
      endif
c
 20   continue
      read(*,*,iostat=ios) icase,mfact0,icodein,mctadj_in,mtilt_in,hlid,
     &     ppcoef,dgridi,ht0in,elbasein,zb1in,ze1in,szb1in,szm1in,
     &     sze1in,zb2in,ze2in,szb2in,sze2in,tb1in,te1in,tb2in,te2in,
     &     zfinalin,vsetlin
      if(ios.ne.0) goto 999
      mctadj=mctadj_in
      mtilt=mtilt_in
      icode=icodein
      zb1=zb1in
      ze1=ze1in
      zb2=zb2in
      ze2=ze2in
      szb1=szb1in
      szm1=szm1in
      sze1=sze1in
      szb2=szb2in
      sze2=sze2in
      tb1=tb1in
      te1=te1in
      tb2=tb2in
      te2=te2in
      vsetl=vsetlin
      ht0(1)=ht0in
      elbase(1)=elbasein
      zfinal(1)=zfinalin
      value=vcbar(1,mfact0,hlid,ppcoef,lcalm)
      write(*,'(i8,1x,es20.12)') icase,value
      goto 20
c
 999  continue
      end
